from rest_framework import status
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

        utc_time, target_time, start_time, end_time = services.get_time()
        commit_lines = services.get_commit_lines(payload)

        if not commit_lines:
            return Response("No Change")

        blob_name = f"github/{event_type}/{event_id}.json"
        data = {
            "id": event_id,
            "user_id": payload["sender"]["id"],
            "commit_lines": [
                {"extension": k, "num": v} for k, v in commit_lines.items()
            ],
            "updated_at": utc_time.strftime("%Y-%m-%d %H:%M:%S"),
            "repository": payload["repository"]["full_name"],
            "private": payload["repository"]["private"],
        }

        services.upload_blob(blob_name, data)

        return Response(data)


class GitHubPushJob(APIView):
    def get(self, request, format=None):
        services.add_data_to_bigquery()
        services.delete_blob()
        return Response("SUCCESS")
