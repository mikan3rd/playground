import os
import re
from datetime import datetime
from pprint import pprint

import dateutil.parser
import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from pytz import timezone

from helpers.twitter_api import TwitterApiClient

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

github_base_url = "https://api.github.com"
base_params = {"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET}


def aggrigate_and_tweet(commitly_user, utc_time, target_time, start_time, end_time):
    github_user = get_user_from_github(commitly_user)
    username = github_user["login"]
    print("username:", username)

    github_contribution = get_contribution_from_github(username)

    commit_result = get_commit_lines_from_github(username, start_time, end_time)
    aggrigate_result = aggrigate_commit_lines(commit_result)

    tweet_commit(
        commitly_user, github_user, github_contribution, aggrigate_result, start_time
    )


def get_user_from_github(commitly_user):

    url = f"{github_base_url}/user"
    response = requests.get(
        url, headers={"Authorization": f"token {commitly_user['github_access_token']}"}
    )
    print(response.status_code)
    result = response.json()
    return result


def get_contribution_from_github(username: str):
    url = f"https://github.com/users/{username}/contributions"
    response = requests.get(url)

    soup = BeautifulSoup(response.content, "lxml")
    rect_list = soup.find_all("rect")

    contributions = {}
    for rect in rect_list:
        date = rect.get("data-date")
        count = rect.get("data-count")
        color = rect.get("fill")
        if not date or count is None:
            continue
        contributions[date] = {
            "count": int(count),
            "color": color,
            "level": contribute_colors.get(color),
        }

    return contributions


def get_commit_lines_from_github(username: str, start_time, end_time):
    # TODO: ページング対応

    url = f"{github_base_url}/users/{username}/events"
    params = {"per_page": 100}
    params.update(base_params)

    response = requests.get(url, params=params)
    events = response.json()

    result = {"no_extension": 0}

    for event in events:

        if not event["type"] == "PushEvent":
            continue

        created_at = dateutil.parser.parse(event["created_at"])

        if created_at < start_time:
            break

        if not start_time < created_at < end_time:
            continue

        for commit in event["payload"]["commits"]:

            if not commit["distinct"]:
                continue

            print(event["created_at"], event["repo"]["name"])
            response = requests.get(commit["url"], params=params)
            commit_detail = response.json()
            files = commit_detail.get("files")

            if not files:
                pprint(response)

            for file_ in files:
                changes = file_["changes"]

                if changes == 0:
                    continue

                search_result = re.search(r"\.\w+$", file_["filename"])

                if not search_result:
                    result["no_extension"] += changes
                    continue

                extension = search_result.group()
                if not result.get(extension):
                    result[extension] = 0

                result[extension] += changes

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


contribute_colors = {
    "#ebedf0": 1,
    "#c6e48b": 2,
    "#7bc96f": 3,
    "#239a3b": 4,
    "#196127": 5,
}

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
    "others": "その他",
}
