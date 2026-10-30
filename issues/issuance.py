"""
Issuing blood against an approved request (E5-S2, E3-S4, E6-S6).

Everything happens inside one database transaction:
  1. Claim the request: Approved -> Fulfilled. Only one caller can win.
  2. Lock the usable donation batches for the blood group.
  3. Check that enough unexpired units remain. Stock can never go negative.
  4. Take units from the batches expiring soonest first.
  5. Save the BloodIssue and its allocations.

If any step fails, the whole transaction is rolled back: the request stays
Approved and no stock moves.
"""

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from blood_requests.models import BloodRequest
from donations.models import Donation

from .models import BloodIssue, BloodIssueAllocation


class IssueError(Exception):
    """Base class for issuance refusals. The message is safe to show users."""


class RequestNotApproved(IssueError):
    """The request is not in the Approved state."""


class InsufficientStock(IssueError):
    """Not enough unexpired units of the requested blood group."""


def issue_blood(blood_request, issued_by):
    today = timezone.localdate()
    now = timezone.now()
    units_needed = blood_request.units_required
    blood_group = blood_request.blood_group

    with transaction.atomic():
        # Step 1: claim the request. If another user already issued it,
        # or it is not Approved, this updates 0 rows.
        claimed = BloodRequest.objects.filter(
            pk=blood_request.pk,
            status=BloodRequest.Status.APPROVED,
        ).update(
            status=BloodRequest.Status.FULFILLED,
            updated_at=now,
        )

        if claimed == 0:
            raise RequestNotApproved(
                f"Request {blood_request.pk} is not Approved, "
                f"so blood cannot be issued for it."
            )

        # Step 2: lock the batches. Concurrent issues for the same blood
        # group wait here until this transaction finishes.
        batches = list(
            Donation.objects.select_for_update()
            .filter(
                blood_group=blood_group,
                donation_status=Donation.DonationStatus.ACCEPTED,
                expiry_date__gte=today,
            )
            .order_by("expiry_date", "donation_date", "pk")
        )

        issued_so_far = {
            row["donation"]: row["total"]
            for row in (
                BloodIssueAllocation.objects.filter(donation__in=batches)
                .values("donation")
                .annotate(total=Sum("units"))
            )
        }

        # Step 3: work out what is left in each batch.
        plan = []
        for batch in batches:
            left = batch.quantity_units - issued_so_far.get(batch.pk, 0)
            if left > 0:
                plan.append((batch, left))

        available = sum(left for _batch, left in plan)

        if available < units_needed:
            # Raising here rolls back the status claim from step 1.
            raise InsufficientStock(
                f"Only {available} unit(s) of {blood_group} are available, "
                f"but {units_needed} are required."
            )

        # Step 4 and 5: record the issue and take units, earliest expiry first.
        issue = BloodIssue.objects.create(
            blood_request=blood_request,
            blood_group=blood_group,
            units_issued=units_needed,
            issued_by=issued_by,
        )

        still_needed = units_needed
        for batch, left in plan:
            if still_needed == 0:
                break
            take = min(left, still_needed)
            BloodIssueAllocation.objects.create(
                issue=issue,
                donation=batch,
                units=take,
            )
            still_needed -= take

    # Keep the caller's in-memory object in sync with the database.
    blood_request.status = BloodRequest.Status.FULFILLED
    blood_request.updated_at = now

    return issue