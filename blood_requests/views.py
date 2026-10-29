from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .forms import BloodRequestForm
from .permissions import can_submit_request


@login_required
def submit_request(request):
    """
    E4-S2: Submit a blood request with validation.

    Covers FR-6.1, FR-6.2, FR-6.3, FR-6.4 and FR-6.7.
    """
    if not can_submit_request(request.user):
        raise PermissionDenied(
            "You are not authorized to submit blood requests."
        )

    if request.method == "POST":
        form = BloodRequestForm(request.POST)

        if form.is_valid():
            blood_request = form.save(commit=False)
            blood_request.requested_by = request.user
            blood_request.save()

            messages.success(
                request,
                f"Blood request {blood_request.request_id} submitted "
                f"for {blood_request.units_required} unit(s) of "
                f"{blood_request.blood_group}. "
                f"Status: {blood_request.status}.",
            )

            return redirect("blood_requests:submit")

    else:
        initial = {}

        blood_group = request.GET.get("blood_group", "").strip()

        if blood_group:
            initial["blood_group"] = blood_group

        form = BloodRequestForm(initial=initial)

    return render(
        request,
        "blood_requests/submit.html",
        {
            "form": form,
        },
    )
