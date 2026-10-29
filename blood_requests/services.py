"""
Business rules for reviewing blood requests (E5-S1, FR-7.1).

Allowed status changes:
    Pending -> Approved
    Pending -> Rejected
Anything else (e.g. approving an already rejected request) is refused.
"""

from django.utils import timezone

from .models import BloodRequest


class RequestAlreadyReviewed(Exception):
    """Raised when a request is no longer Pending."""


def _review(blood_request, reviewer, new_status, note=""):
    now = timezone.now()

    # A single conditional UPDATE: it only matches while the request is
    # still Pending, so two staff members clicking at the same moment
    # cannot both succeed (the second one updates 0 rows).
    updated_rows = BloodRequest.objects.filter(
        pk=blood_request.pk,
        status=BloodRequest.Status.PENDING,
    ).update(
        status=new_status,
        reviewed_by=reviewer,
        reviewed_at=now,
        review_note=note,
        updated_at=now,
    )

    if updated_rows == 0:
        raise RequestAlreadyReviewed(
            f"Request {blood_request.pk} has already been reviewed."
        )


def approve_request(blood_request, reviewer, note=""):
    _review(blood_request, reviewer, BloodRequest.Status.APPROVED, note)


def reject_request(blood_request, reviewer, note=""):
    _review(blood_request, reviewer, BloodRequest.Status.REJECTED, note)