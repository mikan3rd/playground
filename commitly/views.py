from pprint import pprint

from django.http.response import JsonResponse
from rest_framework.views import APIView

from . import services


class Tweet(APIView):
    def get(self, request, format=None):
        username = "mikan3rd"

        commit_result = services.get_commit_lines_from_github(username)
        aggrigate_result = services.aggrigate_commit_lines(commit_result)

        pprint(aggrigate_result)

        if aggrigate_result["total"] > 0:
            github_user = services.get_user_from_github(username)
            github_contribution = services.get_contribution_from_github(username)
            services.tweet_commit(github_user, github_contribution, aggrigate_result)

        return JsonResponse(aggrigate_result)
