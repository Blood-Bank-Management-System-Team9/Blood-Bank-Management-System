from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from donors.models import Donor

from .forms import DonationRecordingForm


@login_required
@require_POST
def record_donation(request):
    """
    Record a blood donation for a registered donor.

    Only authenticated Blood Bank Staff may record donations.
    """

    if not request.user.groups.filter(
        name="Blood Bank Staff"
    ).exists():
        raise PermissionDenied(
            "You are not authorized to record donations."
        )

    donor_id = request.POST.get("donor_id", "").strip()

    donor = get_object_or_404(
        Donor,
        donor_id=donor_id,
    )

    form = DonationRecordingForm(request.POST)

    if form.is_valid():
        donation = form.save(commit=False)

        donation.donor = donor
        donation.save()

        messages.success(
            request,
            f"Donation {donation.donation_id} recorded successfully "
            f"for {donor.full_name}.",
        )

    else:
        for field_name, errors in form.errors.items():

            if field_name in form.fields:
                label = form.fields[field_name].label
            else:
                label = "Donation"

            for error in errors:
                messages.error(
                    request,
                    f"{label}: {error}",
                )

    search_url = reverse("donors:search")

    query_string = urlencode(
        {
            "phone_number": donor.phone_number,
        }
    )

    return redirect(
        f"{search_url}?{query_string}"
    )