from django.urls import path

from . import views


app_name = "donors"


urlpatterns = [
    path(
        "register/",
        views.register_donor,
        name="register",
    ),
]