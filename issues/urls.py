from django.urls import path

from . import views


app_name = "issues"


urlpatterns = [
    path(
        "<str:request_id>/",
        views.issue_request,
        name="issue",
    ),
]