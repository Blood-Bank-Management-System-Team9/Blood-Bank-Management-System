from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from blood_requests.permissions import can_submit_request

from .services import BLOOD_GROUPS, get_available_units, is_valid_blood_group


ALLOWED_ROLES = [
    "Blood Bank Staff",
    "Hospital Staff",
    "Administrator",
]


def can_search_availability(user):
    """
    FR-5.1: blood availability search is available to authorized users
    (Blood Bank Staff, Hospital Staff and Administrator).
    """
    if user.is_superuser:
        return True

    return user.groups.filter(name__in=ALLOWED_ROLES).exists()


@login_required
def search_availability(request):
    """
    E4-S1: Search blood availability by blood group.

    Covers FR-5.1 to FR-5.4.
    """
    if not can_search_availability(request.user):
        raise PermissionDenied(
            "You are not authorized to search blood availability."
        )

    blood_group = request.GET.get("blood_group", "").strip()

    result = None

    if blood_group:
        if is_valid_blood_group(blood_group):
            available_units = get_available_units(blood_group)

            result = {
                "blood_group": blood_group,
                "available_units": available_units,
                "is_available": available_units > 0,
            }
        else:
            messages.error(
                request,
                "Please select a valid blood group.",
            )

    return render(
        request,
        "blood_search/search.html",
        {
            "blood_groups": BLOOD_GROUPS,
            "selected_blood_group": blood_group,
            "result": result,
            "can_request": can_submit_request(request.user),
        },
    )
