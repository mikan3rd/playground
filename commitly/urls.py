from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = format_suffix_patterns(
    [
        path("tweet", views.Tweet.as_view()),
        path("github_webhook", views.GitHubWebhook.as_view()),
        path("github_push_job", views.GitHubPushJob.as_view()),
    ]
)
