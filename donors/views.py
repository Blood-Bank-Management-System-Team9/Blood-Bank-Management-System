from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DonorRegistrationForm, DonorUpdateForm
from .models import Donor


def is_blood_bank_staff(user):
    """
    Return True if the authenticated user belongs to the
    Blood Bank Staff role.
    """
    return user.groups.filter(name="Blood Bank Staff").exists()


@login_required
def register_donor(request):
    """
    Register a new donor.

    Only authenticated Blood Bank Staff are allowed to perform
    donor registration.
    """
    if not is_blood_bank_staff(request.user):
        raise PermissionDenied(
            "You are not authorized to register donors."
        )

    if request.method == "POST":
        form = DonorRegistrationForm(request.POST)

        if form.is_valid():
            donor = form.save()

            messages.success(
                request,
                f"Donor {donor.full_name} registered successfully "
                f"with Donor ID {donor.donor_id}.",
            )

            return redirect("donors:register")

    else:
        form = DonorRegistrationForm()

    return render(
        request,
        "donors/register.html",
        {
            "form": form,
        },
    )


@login_required
def search_donor(request):
    """
    Search for an existing donor by phone number.

    Only authenticated Blood Bank Staff may search donor records.
    """
    if not is_blood_bank_staff(request.user):
        raise PermissionDenied(
            "You are not authorized to search donor records."
        )

    phone_number = request.GET.get("phone_number", "").strip()

    donors = Donor.objects.none()

    if phone_number:
        donors = Donor.objects.filter(
            phone_number=phone_number
        )

    return render(
        request,
        "donors/search.html",
        {
            "phone_number": phone_number,
            "donors": donors,
        },
    )


@login_required
def update_donor(request, donor_id):
    """
    Update an existing donor's editable information.

    Only authenticated Blood Bank Staff may update donor records.
    """
    if not is_blood_bank_staff(request.user):
        raise PermissionDenied(
            "You are not authorized to update donor records."
        )

    donor = get_object_or_404(
        Donor,
        donor_id=donor_id,
    )

    if request.method == "POST":
        form = DonorUpdateForm(
            request.POST,
            instance=donor,
        )

        if form.is_valid():
            donor = form.save()

            messages.success(
                request,
                f"Donor {donor.full_name} updated successfully.",
            )

            return redirect(
                "donors:update",
                donor_id=donor.donor_id,
            )

    else:
        form = DonorUpdateForm(
            instance=donor,
        )

    return render(
        request,
        "donors/update.html",
        {
            "form": form,
            "donor": donor,
        },
    )