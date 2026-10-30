from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from blood_requests.models import BloodRequest
from inventory.services import get_available_units

from .issuance import IssueError, issue_blood
from .models import BloodIssue
from .permissions import can_issue_blood


@login_required
def issue_request(request, request_id):
    """
    E5-S2: show an approved request and its stock, then issue the blood.
    POST performs the issue; GET only displays.
    """
    if not can_issue_blood(request.user):
        raise PermissionDenied("You are not authorized to issue blood.")

    blood_request = get_object_or_404(BloodRequest, pk=request_id)

    if request.method == "POST":
        try:
            issue = issue_blood(blood_request, request.user)
        except IssueError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request,
                f"{issue.units_issued} unit(s) of {issue.blood_group} "
                f"issued for request {blood_request.request_id}.",
            )

        # Post/redirect/get: refreshing the page never repeats the issue.
        return redirect("issues:issue", request_id=blood_request.request_id)

    issue = BloodIssue.objects.filter(blood_request=blood_request).first()
    available_units = get_available_units(blood_request.blood_group)

    can_issue = (
        blood_request.status == BloodRequest.Status.APPROVED
        and available_units >= blood_request.units_required
    )

    return render(
        request,
        "issues/issue_request.html",
        {
            "blood_request": blood_request,
            "issue": issue,
            "available_units": available_units,
            "can_issue": can_issue,
        },
    )