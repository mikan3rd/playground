import os
from time import time

import jwt
import requests
from bs4 import BeautifulSoup

app_id = "25466"
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

github_base_url = "https://api.github.com"
base_params = {"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET}

contribute_colors = {
    "#ebedf0": 1,
    "#c6e48b": 2,
    "#7bc96f": 3,
    "#239a3b": 4,
    "#196127": 5,
}


class GitHubApiClient:
    def __init__(self, user_token=None):
        self.app_token = None
        self.installation_token = None
        self.user_token = user_token

    def get_app_token(self):
        with open("github_app.pem", "r") as f:
            private_key = f.read()

        now = int(time())
        payload = {"iat": now, "exp": now + (10 * 60), "iss": app_id}
        app_token = jwt.encode(payload, private_key, algorithm="RS256").decode("utf-8")

        self.app_token = app_token
        return app_token

    def get_app_header(self):
        headers = {
            "Authorization": f"Bearer {self.app_token}",
            "Accept": "application/vnd.github.machine-man-preview+json",
        }
        return headers

    def get_installation_header(self):
        headers = {
            "Authorization": f"Bearer {self.installation_token}",
            "Accept": "application/vnd.github.machine-man-preview+json",
        }
        return headers

    def get_user_header(self):
        headers = {"Authorization": f"token {self.user_token}"}
        return headers

    def get_repository_installation_token(self, owner, repo):
        headers = self.get_app_header()
        url = f"{github_base_url}/repos/{owner}/{repo}/installation"
        response = requests.get(url, headers=headers).json()
        access_token_url = response.get("access_tokens_url")

        if not access_token_url:
            return False

        response = requests.post(access_token_url, headers=headers).json()
        installation_token = response["token"]

        self.installation_token = installation_token
        return installation_token

    def get_user_installation_token(self, username):
        headers = self.get_app_header()
        url = f"{github_base_url}/users/{username}/installation"
        response = requests.get(url, headers=headers).json()
        access_token_url = response.get("access_tokens_url")

        if not access_token_url:
            return False

        response = requests.post(access_token_url, headers=headers).json()
        installation_token = response["token"]

        self.installation_token = installation_token
        return installation_token

    def get_organization_installation_token(self, org_name):
        headers = self.get_app_header()
        url = f"{github_base_url}/orgs/{org_name}/installation"
        response = requests.get(url, headers=headers).json()

        access_token_url = response.get("access_tokens_url")
        if not access_token_url:
            return False

        response = requests.post(access_token_url, headers=headers).json()
        installation_token = response["token"]

        self.installation_token = installation_token
        return installation_token

    def get_user(self):
        headers = self.get_user_header()
        url = f"{github_base_url}/user"
        response = requests.get(url, headers=headers)
        return response.json()

    def get_user_organizations(self):
        headers = self.get_user_header()
        url = f"{github_base_url}/user/orgs"
        response = requests.get(url, headers=headers)
        return response.json()

    def get_installation_repositories(self):
        headers = self.get_installation_header()
        url = f"{github_base_url}/installation/repositories"
        response = requests.get(url, headers=headers)
        return response.json()

    def get_commit_detail(self, owner, repo, commit_id):
        headers = self.get_installation_header()
        url = f"{github_base_url}/repos/{owner}/{repo}/commits/{commit_id}"
        response = requests.get(url, headers=headers)
        return response.json()

    def get_contribution_from_github(self, username: str):
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
