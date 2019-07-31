from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.http.response import JsonResponse
from pytz import timezone
from rest_framework.views import APIView

from . import services


class Tweet(APIView):
    def get(self, request, format=None):

        utc_time = datetime.now(timezone("UTC"))
        target_time = utc_time - relativedelta(days=1)
        start_time = target_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = utc_time.replace(hour=0, minute=0, second=0, microsecond=0)

        print("utc_time:   ", utc_time)
        print("target_time:", target_time)
        print("start_time: ", start_time)
        print("end_time:   ", end_time)

        github_user = services.get_user_from_github()
        username = github_user["login"]
        print("username:", username)

        github_contribution = services.get_contribution_from_github(username)

        commit_result = services.get_commit_lines_from_github(
            username, start_time, end_time
        )
        aggrigate_result = services.aggrigate_commit_lines(commit_result)

        services.tweet_commit(
            github_user, github_contribution, aggrigate_result, start_time
        )

        return JsonResponse(aggrigate_result)
