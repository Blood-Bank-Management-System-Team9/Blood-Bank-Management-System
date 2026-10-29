from django.urls import path

from . import views


app_name = "blood_requests"


# NOTE: "new/" and "pending/" must stay ABOVE "<str:request_id>/",
# otherwise Django would treat the words "new"/"pending" as a request ID.
urlpatterns = [
    path(
        "new/",
        views.submit_request,
        name="submit",
    ),
    path(
        "pending/",
        views.pending_requests,
        name="pending",
    ),
    path(
        "<str:request_id>/",
        views.request_detail,
        name="detail",
    ),
]