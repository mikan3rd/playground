from django.http.response import JsonResponse
from rest_framework.views import APIView


class SlackLunchTest(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def get(self, request, format=None):
        return JsonResponse({'test': 'GET'})

    def post(self, request, format=None):
        return JsonResponse({'test': 'POST'})
