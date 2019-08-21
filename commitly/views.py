from django.http.response import JsonResponse
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

        return JsonResponse({"result": "SUCCESS!!"})
