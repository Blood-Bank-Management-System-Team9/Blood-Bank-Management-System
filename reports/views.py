from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.utils import timezone

from inventory.services import get_inventory_by_blood_group, get_low_stock_groups

from .forms import ReportFilterForm
from .permissions import can_view_reports
from .services import (
    ROW_LIMIT,
    build_group_rows,
    build_summary,
    donation_history,
    issue_history,
    request_history,
)


def default_filters():
    """
    Last 30 days, all blood groups, all statuses.
    """
    today = timezone.localdate()

    return {
        "start_date": today - timedelta(days=30),
        "end_date": today,
        "blood_group": "",
        "donation_status": "",
        "request_status": "",
    }


@login_required
def reports_home(request):
    """
    E5-S3: donation, request and issue history, current stock, and
    operational totals for a date range (FR-8.1 to FR-8.5).
    """
    if not can_view_reports(request.user):
        raise PermissionDenied("You are not authorized to view reports.")

    defaults = default_filters()
    form = ReportFilterForm(request.GET or None, initial=defaults)

    # If the form is valid, blank dates fall back to the defaults.
    # If it is invalid, the errors are shown and the defaults are used.
    if form.is_valid():
        filters = {
            key: form.cleaned_data[key] or defaults[key]
            for key in defaults
        }
    else:
        filters = defaults

    start = filters["start_date"]
    end = filters["end_date"]
    group = filters["blood_group"]

    donations = donation_history(start, end, group, filters["donation_status"])
    requests = request_history(start, end, group, filters["request_status"])
    issues = issue_history(start, end, group)

    return render(
        request,
        "reports/home.html",
        {
            "form": form,
            "filters": filters,
            "summary": build_summary(start, end, group),
            "group_rows": build_group_rows(start, end),
            "inventory": get_inventory_by_blood_group(),
            "low_stock": get_low_stock_groups(),
            "donations": donations[:ROW_LIMIT],
            "donations_total": donations.count(),
            "requests": requests[:ROW_LIMIT],
            "requests_total": requests.count(),
            "issues": issues[:ROW_LIMIT],
            "issues_total": issues.count(),
            "row_limit": ROW_LIMIT,
        },
    )
