from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from inventory.services import get_available_units

from .forms import BloodRequestForm, ReviewDecisionForm
from .models import BloodRequest
from .permissions import can_review_request, can_submit_request
from .services import (
    RequestAlreadyReviewed,
    approve_request,
    reject_request,
)


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

            return redirect("blood_requests:mine")

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


@login_required
def pending_requests(request):
    """
    E5-S1: list of requests waiting for review (oldest first).
    """
    if not can_review_request(request.user):
        raise PermissionDenied(
            "You are not authorized to review blood requests."
        )

    pending = (
        BloodRequest.objects.filter(status=BloodRequest.Status.PENDING)
        .select_related("requested_by")
        .order_by("created_at")
    )

    return render(
        request,
        "blood_requests/pending.html",
        {
            "pending_requests": pending,
        },
    )


@login_required
def request_detail(request, request_id):
    """
    E5-S1: open one request, then approve or reject it (POST only
    changes data). Covers FR-7.1.
    """
    if not can_review_request(request.user):
        raise PermissionDenied(
            "You are not authorized to review blood requests."
        )

    blood_request = get_object_or_404(BloodRequest, pk=request_id)

    if request.method == "POST":
        form = ReviewDecisionForm(request.POST)
        decision = request.POST.get("decision")

        if decision not in ("approve", "reject"):
            messages.error(request, "Please choose Approve or Reject.")

        elif form.is_valid():
            note = form.cleaned_data["note"]

            try:
                if decision == "approve":
                    approve_request(blood_request, request.user, note)
                    outcome = "approved"
                else:
                    reject_request(blood_request, request.user, note)
                    outcome = "rejected"

            except RequestAlreadyReviewed:
                messages.error(
                    request,
                    f"Request {blood_request.request_id} has already "
                    f"been reviewed.",
                )
                return redirect(
                    "blood_requests:detail",
                    request_id=blood_request.request_id,
                )

            messages.success(
                request,
                f"Blood request {blood_request.request_id} {outcome}.",
            )

            return redirect("blood_requests:pending")

    else:
        form = ReviewDecisionForm()

    available_units = get_available_units(blood_request.blood_group)

    return render(
        request,
        "blood_requests/detail.html",
        {
            "blood_request": blood_request,
            "form": form,
            "available_units": available_units,
            "stock_is_short": available_units < blood_request.units_required,
        },
    )

def _status_filter(request):
    """
    Read an optional ?status= filter. Unknown values are ignored.
    """
    status = request.GET.get("status", "").strip()

    if status in BloodRequest.Status.values:
        return status

    return ""


@login_required
def my_requests(request):
    """
    E4-S3: the requesting user views the current status of the
    requests they submitted (FR-6.6).

    Users only ever see their own requests.
    """
    if not can_submit_request(request.user):
        raise PermissionDenied(
            "You are not authorized to view blood requests."
        )

    status = _status_filter(request)

    requests_qs = BloodRequest.objects.filter(
        requested_by=request.user,
    ).order_by("-created_at")

    if status:
        requests_qs = requests_qs.filter(status=status)

    return render(
        request,
        "blood_requests/my_requests.html",
        {
            "blood_requests": requests_qs,
            "statuses": BloodRequest.Status.values,
            "selected_status": status,
        },
    )


@login_required
def all_requests(request):
    """
    E4-S3: Blood Bank Staff review all submitted requests, in every
    status, with an optional status filter (FR-6.5).
    """
    if not can_review_request(request.user):
        raise PermissionDenied(
            "You are not authorized to review blood requests."
        )

    status = _status_filter(request)

    requests_qs = (
        BloodRequest.objects.all()
        .select_related("requested_by", "reviewed_by")
        .order_by("-created_at")
    )

    if status:
        requests_qs = requests_qs.filter(status=status)

    return render(
        request,
        "blood_requests/all_requests.html",
        {
            "blood_requests": requests_qs,
            "statuses": BloodRequest.Status.values,
            "selected_status": status,
        },
    )
