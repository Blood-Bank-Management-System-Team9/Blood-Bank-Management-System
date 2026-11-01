"""
Queries behind the reports and history page (E5-S3, FR-8.1 to FR-8.5).

Every function takes a date range (inclusive) and an optional blood group.
Totals are calculated in the database, not by looping over rows in Python.
"""

from django.db.models import Count, Sum

from blood_requests.models import BloodRequest
from donations.models import Donation
from inventory.services import BLOOD_GROUPS, get_available_units
from issues.models import BloodIssue


ROW_LIMIT = 200


def donation_history(start, end, blood_group="", donation_status=""):
    queryset = Donation.objects.select_related("donor").filter(
        donation_date__gte=start,
        donation_date__lte=end,
    )

    if blood_group:
        queryset = queryset.filter(blood_group=blood_group)

    if donation_status:
        queryset = queryset.filter(donation_status=donation_status)

    return queryset.order_by("-donation_date", "-pk")


def request_history(start, end, blood_group="", request_status=""):
    queryset = BloodRequest.objects.select_related("requested_by").filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    )

    if blood_group:
        queryset = queryset.filter(blood_group=blood_group)

    if request_status:
        queryset = queryset.filter(status=request_status)

    return queryset.order_by("-created_at")


def issue_history(start, end, blood_group=""):
    queryset = BloodIssue.objects.select_related(
        "blood_request",
        "issued_by",
    ).filter(
        issued_at__date__gte=start,
        issued_at__date__lte=end,
    )

    if blood_group:
        queryset = queryset.filter(blood_group=blood_group)

    return queryset.order_by("-issued_at")


def build_summary(start, end, blood_group=""):
    accepted = donation_history(
        start, end, blood_group, Donation.DonationStatus.ACCEPTED
    )
    issues = issue_history(start, end, blood_group)
    requests = request_history(start, end, blood_group)

    counts_by_status = {
        row["status"]: row["count"]
        for row in requests.order_by().values("status").annotate(
            count=Count("pk")
        )
    }

    # Keep every status in a fixed order, even when its count is zero.
    requests_by_status = {
        value: counts_by_status.get(value, 0)
        for value, _label in BloodRequest.Status.choices
    }

    return {
        "donations_accepted": accepted.count(),
        "units_donated": accepted.aggregate(total=Sum("quantity_units"))["total"] or 0,
        "issues_count": issues.count(),
        "units_issued": issues.aggregate(total=Sum("units_issued"))["total"] or 0,
        "requests_total": requests.count(),
        "requests_by_status": requests_by_status,
    }


def build_group_rows(start, end):
    """
    One row per blood group.
    Donated and Issued use the date range. Available is the current stock.
    """
    rows = []

    for group in BLOOD_GROUPS:
        donated = Donation.objects.filter(
            blood_group=group,
            donation_status=Donation.DonationStatus.ACCEPTED,
            donation_date__gte=start,
            donation_date__lte=end,
        ).aggregate(total=Sum("quantity_units"))["total"] or 0

        issued = BloodIssue.objects.filter(
            blood_group=group,
            issued_at__date__gte=start,
            issued_at__date__lte=end,
        ).aggregate(total=Sum("units_issued"))["total"] or 0

        rows.append(
            {
                "blood_group": group,
                "donated": donated,
                "issued": issued,
                "available": get_available_units(group),
            }
        )

    return rows