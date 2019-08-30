import json
import re
from datetime import datetime
from pprint import pprint

from dateutil.relativedelta import relativedelta
from google.auth.transport.requests import AuthorizedSession
from google.cloud import bigquery, storage
from google.oauth2 import service_account
from pytz import timezone

from helpers.github_api import GitHubApiClient
from helpers.twitter_api import TwitterApiClient


def aggrigate_and_tweet(commitly_user, utc_time, target_time, start_time, end_time):
    github_api = GitHubApiClient(commitly_user["github_access_token"])

    github_user = github_api.get_user()
    username = github_user["login"]
    print("username:", username)

    github_contribution = github_api.get_contribution_from_github(username)

    commit_result = get_commit_from_bigquery(
        commitly_user["github_user_id"], start_time, end_time
    )
    aggrigate_result = aggrigate_commit_lines(commit_result)

    tweet_commit(
        commitly_user, github_user, github_contribution, aggrigate_result, start_time
    )


def get_github_installation(user_token):
    github_api = GitHubApiClient(user_token)

    github_user = github_api.get_user()
    username = github_user["login"]

    github_api.get_app_token()

    result = []
    if github_api.get_user_installation_token(username):
        data = github_api.get_installation_repositories()
        result.append({"name": username, "repositories": data["repositories"]})

    organizations = github_api.get_user_organizations()
    for org in organizations:
        org_name = org["login"]
        if github_api.get_organization_installation_token(org_name):
            data = github_api.get_installation_repositories()
            result.append({"name": org_name, "repositories": data["repositories"]})

    return {"result": result}


def add_commit_data(event_id, event_type, payload):
    utc_time, target_time, start_time, end_time = get_time()

    result = get_commit_lines(payload)

    if isinstance(result, str):
        return result

    if not result:
        return "No Change"

    blob_name = f"github/{event_type}/{event_id}.json"
    data = {
        "id": event_id,
        "user_id": payload["sender"]["id"],
        "commit_lines": [{"extension": k, "num": v} for k, v in result.items()],
        "updated_at": utc_time.strftime("%Y-%m-%d %H:%M:%S"),
        "repository": payload["repository"]["full_name"],
        "private": payload["repository"]["private"],
    }

    upload_blob(blob_name, data)
    return data


def get_commit_lines(payload):
    github_api = GitHubApiClient()
    github_api.get_app_token()

    owner = payload["repository"]["owner"]["name"]
    repo = payload["repository"]["name"]

    if not github_api.get_repository_installation_token(owner, repo):
        return "Faild to get installation token"

    result = {}

    for commit in payload["commits"]:

        if not commit["distinct"]:
            continue

        commit_detail = github_api.get_commit_detail(owner, repo, commit["id"])
        files = commit_detail.get("files")

        if not files:
            pprint(commit_detail)

        for file_ in files:
            changes = file_["changes"]

            if changes == 0:
                continue

            search_result = re.search(r"\.\w+$", file_["filename"])

            if not search_result:

                if not result.get("no_extension"):
                    result["no_extension"] = changes

                else:
                    result["no_extension"] += changes

                continue

            extension = search_result.group()
            if not result.get(extension):
                result[extension] = 0

            result[extension] += changes

    return result


def upload_blob(blob_name, data):
    storage_client = storage.Client.from_service_account_json("service_account.json")
    bucket = storage_client.get_bucket("staging.commitly-27919.appspot.com")
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(data), content_type="application/json")
    print("FINISH: upload_blob")


def delete_blob():
    storage_client = storage.Client.from_service_account_json("service_account.json")
    bucket = storage_client.get_bucket("staging.commitly-27919.appspot.com")
    blobs = list(bucket.list_blobs(prefix="github/push/"))
    bucket.delete_blobs(blobs)
    print("FINISH: delete_blob")


def add_data_to_bigquery():
    # TODO: load_table_from_json がリリースされたら移行

    client = bigquery.Client.from_service_account_json("service_account.json")
    dataset_id = "github_push"
    table_name = "staging"

    dataset_ref = client.dataset(dataset_id)
    job_config = bigquery.LoadJobConfig()
    job_config.autodetect = True
    job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    uri = "gs://staging.commitly-27919.appspot.com/github/push/*.json"
    load_job = client.load_table_from_uri(
        uri, dataset_ref.table(table_name), job_config=job_config
    )
    print(f"Starting job: {load_job.job_id}")

    load_job.result()
    print("Job finished")

    destination_table = client.get_table(dataset_ref.table(table_name))
    print(f"Loaded {destination_table.num_rows} rows")


def get_commit_from_bigquery(user_id, start_time, end_time):
    client = bigquery.Client.from_service_account_json("service_account.json")

    query = f"""
SELECT sum(cl.num) as total, cl.extension, TIMESTAMP_TRUNC(updated_at, DAY) as date
FROM `commitly-27919.github_push.staging`, unnest(commit_lines) as cl
where (
user_id = {user_id} and
updated_at BETWEEN TIMESTAMP("{start_time.strftime("%Y-%m-%d")}") AND TIMESTAMP("{end_time.strftime("%Y-%m-%d")}")
)
group by cl.extension, date
"""

    query_job = client.query(query)

    result = {}
    for row in query_job:

        extension = row.extension
        if not result.get(extension):
            result[extension] = 0

        result[extension] += row.total

    return result


def aggrigate_commit_lines(commit_result):
    no_extension = commit_result.pop("no_extension", 0)
    main_list = []
    sub_list = []
    total = 0

    for key, value in commit_result.items():
        total += value

        language = extentions.get(key)
        stat = {"language": language, "extention": key, "lines": value}

        if not language:
            sub_list.append(stat)
            continue

        main_list.append(stat)

    main_list = sorted(main_list, key=lambda k: k["lines"], reverse=True)
    sub_list = sorted(sub_list, key=lambda k: k["lines"], reverse=True)

    if no_extension > 0:
        sub_list.append({"language": None, "extention": None, "lines": value})

    result = {"main_list": main_list, "sub_list": sub_list, "total": total}
    return result


def tweet_commit(
    commitly_user, github_user, github_contribution, aggrigate_result, target_time
):
    contribution_time = target_time.strftime("%Y-%m-%d")
    contribution = github_contribution.get(contribution_time)
    print(contribution_time, contribution)
    has_contribution = contribution and contribution["count"] > 0

    if aggrigate_result["total"] == 0 and not has_contribution:
        print("No Commit...")
        return

    twitter_api = TwitterApiClient(
        commitly_user["twitter_access_token"],
        commitly_user["twitter_access_token_secret"],
    )
    response = twitter_api.get_account()
    screen_name = response["screen_name"]

    content_list = [target_time.strftime("%Y年%-m月%-d日(%a)")]

    if aggrigate_result["total"] > 0:
        content_list += [
            f"@{screen_name} さんは{aggrigate_result['total']}行のコードを書きました!",
            "",
        ]

        for d in aggrigate_result["main_list"]:
            content_list.append(f"{d['language']}: {d['lines']}")

        if aggrigate_result["main_list"] and aggrigate_result["sub_list"]:
            content_list.append("")

        for d in aggrigate_result["sub_list"]:
            if not d["extention"]:
                content_list.append(f"その他: {d['lines']}")
                continue

            content_list.append(f"{d['extention']}: {d['lines']}")

    if has_contribution:
        content_list += ["", f"contribution: {contribution['count']}"]

    content_list += ["", f"[GitHub] {github_user['html_url']}", "", "#commitly"]

    status = "\n".join(content_list)

    print("---statsu---")
    print(status)

    response = twitter_api.post_tweet(status)
    if response.get("errors"):
        pprint(response)


def get_time():
    utc_time = datetime.now(timezone("UTC"))
    target_time = utc_time - relativedelta(days=1)
    start_time = target_time.replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = utc_time.replace(hour=0, minute=0, second=0, microsecond=0)

    print("utc_time:   ", utc_time)
    print("target_time:", target_time)
    print("start_time: ", start_time)
    print("end_time:   ", end_time)

    return utc_time, target_time, start_time, end_time


def get_id_token_session(target_audience: str):
    credentials = service_account.IDTokenCredentials.from_service_account_file(
        "service_account.json", target_audience=target_audience
    )
    authed_session = AuthorizedSession(credentials)
    return authed_session


def get_users():
    url = "https://asia-northeast1-commitly-27919.cloudfunctions.net/getUsers"
    authed_session = get_id_token_session(url)
    response = authed_session.get(url)
    result = response.json()
    return result["users"]


extentions = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React",
    ".tsx": "React + TypeScript",
    ".rb": "Ruby",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".php": "PHP",
    ".go": "Go",
    ".sh": "ShellScript",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".cobol": "COBOL",
    ".coffee": "CoffeeScript",
    ".hs": "Haskell",
    ".lisp": "Lisp",
    ".sql": "SQL",
    ".m": "Objective-C",
    ".pl": "Perl",
    ".r": "R",
    ".rs": "Rust",
    ".scala": "Scala",
    ".json": "JSON",
    ".md": "Markdown",
    ".yaml": "YAML",
    "others": "その他",
}
