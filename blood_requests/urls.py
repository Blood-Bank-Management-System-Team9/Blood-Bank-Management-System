from django.urls import path

from . import views


app_name = "blood_requests"


urlpatterns = [
    path(
        "new/",
        views.submit_request,
        name="submit",
    ),
]
