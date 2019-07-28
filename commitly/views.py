import re
from pprint import pprint

import requests
from django.http.response import JsonResponse
from rest_framework.views import APIView

github_base_url = "https://api.github.com"


class Tweet(APIView):
    def get(self, request, format=None):
        username = "mikan3rd"
        url = f"{github_base_url}/users/{username}/events"
        print(url)
        response = requests.get(url).json()

        result = {"others": 0}

        for event in response:

            if not event["type"] == "PushEvent":
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
                    additions = file_["additions"]

                    if not search_result:
                        result["others"] += additions
                        continue

                    extension = search_result.group()
                    if not result.get(extension):
                        result[extension] = 0

                    result[extension] += additions

        pprint(result)
        return JsonResponse(result)
