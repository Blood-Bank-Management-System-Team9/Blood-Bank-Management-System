from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .forms import DonorRegistrationForm


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