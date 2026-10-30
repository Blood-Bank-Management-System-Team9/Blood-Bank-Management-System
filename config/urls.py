"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from donors import views as donor_views
from inventory import views as inventory_views
from issues import views as issues_views


urlpatterns = [
    path("", inventory_views.inventory_dashboard, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("donors/", include("donors.urls")),
    path("blood-search/", include("blood_search.urls")),
    path("requests/", include("blood_requests.urls")),
    path("blood-issue/", include("issues.urls")),
    path("api/issues", issues_views.issue_blood_api, name="api-issues"),
    path("api/", include("donations.urls")),
    path(
        "api/donors/<str:donor_id>",
        donor_views.donor_history,
        name="donor-history",
    ),
    path("inventory/", include("inventory.urls")),
]
