from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class Tweet(APIView):
    def get(self, request, format=None):
        utc_time, target_time, start_time, end_time = services.get_time()
        users = services.get_users()

        for commitly_user in users:
            services.aggrigate_and_tweet(
                commitly_user, utc_time, target_time, start_time, end_time
            )

        return Response({"result": "SUCCESS!!"})


class GitHubWebhook(APIView):
    def post(self, request, format=None):
        print(request.data)
        return Response(request.data)
