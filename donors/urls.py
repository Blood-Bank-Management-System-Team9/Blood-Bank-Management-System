from django.urls import path

from . import views


app_name = "donors"


urlpatterns = [
    path(
        "register/",
        views.register_donor,
        name="register",
    ),
    path(
        "search/",
        views.search_donor,
        name="search",
    ),
    path(
        "<str:donor_id>/update/",
        views.update_donor,
        name="update",
    ),
]
