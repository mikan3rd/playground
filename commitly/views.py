import re
from datetime import datetime
from pprint import pprint

import dateutil.parser
import pytz
import requests
from dateutil.relativedelta import relativedelta
from django.http.response import JsonResponse
from rest_framework.views import APIView

tz = pytz.timezone("Asia/Tokyo")
github_base_url = "https://api.github.com"


class Tweet(APIView):
    def get(self, request, format=None):
        username = "mikan3rd"
        url = f"{github_base_url}/users/{username}/events"
        response = requests.get(url).json()

        result = {"others": 0}
        now = datetime.now(tz)
        print(now)

        for event in response:

            if not event["type"] == "PushEvent":
                continue

            created_at = dateutil.parser.parse(event["created_at"])

            if now - relativedelta(days=1) > created_at:
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
                        result["others"] += changes
                        continue

                    extension = search_result.group()
                    if not result.get(extension):
                        result[extension] = 0

                    result[extension] += changes

        return JsonResponse(result)
