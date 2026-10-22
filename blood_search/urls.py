from django.urls import path

from . import views


app_name = "blood_search"


urlpatterns = [
    path(
        "",
        views.search_availability,
        name="availability",
    ),
]
