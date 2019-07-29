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

        # services.tweet_commit(aggrigate_result)

        return JsonResponse(aggrigate_result)
