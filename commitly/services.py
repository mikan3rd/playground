import os
import re
from pprint import pprint

import dateutil.parser
import requests
from bs4 import BeautifulSoup

from helpers.twitter_api import TwitterApiClient

github_base_url = "https://api.github.com"


TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")


def get_user_from_github(username: str):
    url = f"{github_base_url}/users/{username}"
    response = requests.get(url).json()
    return response


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
            "count": count,
            "color": color,
            "level": contribute_colors.get(color),
        }

    return contributions


def get_commit_lines_from_github(username: str, start_time, end_time):
    # TODO: ページング対応

    url = f"{github_base_url}/users/{username}/events"
    response = requests.get(url, params={"per_page": 100}).json()

    result = {"no_extension": 0}

    for event in response:

        if not event["type"] == "PushEvent":
            continue

        created_at = dateutil.parser.parse(event["created_at"])
        print(created_at)

        if not start_time < created_at < end_time:
            continue

        for commit in event["payload"]["commits"]:

            if not commit["distinct"]:
                continue

            print(event["created_at"], event["repo"]["name"])
            response = requests.get(commit["url"]).json()

            if not response.get("files"):
                pprint(response)

            for file_ in response.get("files", []):
                search_result = re.search(r"\.\w+$", file_["filename"])
                changes = file_["changes"]

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


def tweet_commit(github_user, github_contribution, aggrigate_result, target_time):
    contribution = github_contribution.get(target_time.strftime("%Y-%m-%-d"))

    if aggrigate_result["total"] == 0 and contribution["count"] == 0:
        print("No Commit...")
        return

    content_list = [target_time.strftime("%Y年%-m月%-d日(%a)")]

    if aggrigate_result["total"] > 0:
        content_list += [
            f"{github_user['login']} さんは{aggrigate_result['total']}行のコードを書きました!",
            "",
        ]

        for d in aggrigate_result["main_list"]:
            content_list.append(f"{d['language']}: {d['lines']}")

        for d in aggrigate_result["sub_list"]:
            if not d["extention"]:
                content_list.append(f"その他: {d['lines']}")
                continue

            content_list.append(f"{d['extention']}: {d['lines']}")

    if contribution:
        content_list += ["", f"contribution: {contribution['count']}"]

    content_list += ["", f"[GitHub] {github_user['html_url']}", "", "#commitly"]

    status = "\n".join(content_list)

    print("---statsu---")
    print(status)

    twitter_api = TwitterApiClient(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    response = twitter_api.post_tweet(status)
    pprint(response)


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
    ".tsx": "React",
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
    ".jsx": "JSX",
    ".lisp": "Lisp",
    ".sql": "SQL",
    ".m": "Objective-C",
    ".pl": "Perl",
    ".r": "R",
    ".rs": "Rust",
    ".scala": "Scala",
    "others": "その他",
}
