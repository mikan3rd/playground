from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services


class Tweet(APIView):
    def get(self, request, format=None):
        utc_time, target_time, start_time, end_time = services.get_time()
        users = services.get_users()

        for commitly_user in users:
            try:
                services.aggrigate_and_tweet(
                    commitly_user, utc_time, target_time, start_time, end_time
                )

            except Exception as e:
                print("ERROR:", e)
                continue

        return Response({"result": "SUCCESS!!"})


class GitHubWebhook(APIView):
    def post(self, request):
        event_id = request.META.get("HTTP_X_GITHUB_DELIVERY")
        event_type = request.META.get("HTTP_X_GITHUB_EVENT")

        if not event_id or not event_type:
            return Response(status=status.HTTP_403_FORBIDDEN)

        if event_type not in ["push"]:
            return Response("Not Match Event")

        payload = request.data

        if not payload.get("commits"):
            return Response("SKIP")

        result = services.add_commit_data(event_id, event_type, payload)
        return Response(result)


class GitHubPushJob(APIView):
    def get(self, request, format=None):
        services.add_data_to_bigquery()
        services.delete_blob()
        return Response("SUCCESS")


class GitHubInstallation(APIView):
    def get(self, request, format=None):
        user_access_token = request.query_params.get("github_access_token")
        if not user_access_token:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        result = services.get_github_installation(user_access_token)
        return Response(result)
