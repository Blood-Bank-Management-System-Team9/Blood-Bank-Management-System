
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from inventory.services import (
    get_inventory_by_blood_group,
    get_low_stock_groups,
    get_near_expiry_donations,
    get_expired_donations,
)

ALLOWED_ROLES = [
    "Blood Bank Staff",
    "Hospital Staff",
    "Administrator",
]


@login_required
def inventory_dashboard(request):
    if not (
        request.user.is_superuser
        or request.user.groups.filter(name__in=ALLOWED_ROLES).exists()
    ):
        raise PermissionDenied(
            "You are not authorized to view blood inventory."
        )

    inventory = get_inventory_by_blood_group()
    low_stock = get_low_stock_groups()

    context = {
        "inventory": inventory,
        "low_stock": low_stock,
        "near_expiry_donations": get_near_expiry_donations(),
        "expired_donations": get_expired_donations(),
    }

    return render(request, "inventory/dashboard.html", context)
