from django.urls import path

from . import views


app_name = "donations"


urlpatterns = [
    path(
        "donations",
        views.record_donation,
        name="record",
    ),
]