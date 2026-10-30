import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from blood_requests.models import BloodRequest
from inventory.services import get_available_units

from .issuance import IssueError, InsufficientStock, RequestNotApproved, issue_blood
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


def _read_request_id(request):
    """
    Read request_id from a JSON body or from form data.
    """
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return ""
        value = data.get("request_id", "") if isinstance(data, dict) else ""
    else:
        value = request.POST.get("request_id", "")

    return str(value).strip()


@require_http_methods(["POST"])
def issue_blood_api(request):
    """
    POST /api/issues

    Body (JSON or form): request_id=<id of an Approved request>

    Same rules as the issue page: only Blood Bank Staff, and the issue is
    all-or-nothing. The work is done by issue_blood(), the same function
    the issue page uses.

    Responses:
      201  issued
      400  request_id missing
      401  not logged in
      403  logged in but not Blood Bank Staff
      404  no request with that id
      409  request not Approved (already issued, pending, rejected),
           or not enough unexpired stock
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "authentication_required"}, status=401)

    if not can_issue_blood(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    request_id = _read_request_id(request)
    if not request_id:
        return JsonResponse({"error": "request_id_required"}, status=400)

    blood_request = BloodRequest.objects.filter(pk=request_id).first()
    if blood_request is None:
        return JsonResponse({"error": "request_not_found"}, status=404)

    try:
        issue = issue_blood(blood_request, request.user)
    except RequestNotApproved:
        return JsonResponse({"error": "request_not_approved"}, status=409)
    except InsufficientStock as error:
        return JsonResponse(
            {"error": "insufficient_stock", "detail": str(error)},
            status=409,
        )

    return JsonResponse(
        {
            "issue_id": issue.issue_id,
            "request_id": blood_request.request_id,
            "blood_group": issue.blood_group,
            "units_issued": issue.units_issued,
            "issued_at": issue.issued_at.isoformat(),
        },
        status=201,
    )