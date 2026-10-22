"""
Availability lookups used by the Blood Availability Search (E4-S1).

TEMPORARY SOURCE OF TRUTH:
The Blood Inventory app (E3) is not merged yet, so availability is
currently derived from Accepted, non-expired donations. Once the
inventory app exposes its own availability function, replace the body
of get_available_units() with a call to it. The view and tests do not
need to change, because they only depend on this function.
"""

from django.db.models import Sum
from django.utils import timezone

from donations.models import Donation
from donors.models import Donor


BLOOD_GROUPS = [value for value, _label in Donor.BloodGroup.choices]


def is_valid_blood_group(blood_group):
    return blood_group in BLOOD_GROUPS


def get_available_units(blood_group):
    """
    Return the number of available units for one blood group.

    FR-5.2: shows the current available quantity.
    FR-5.3 / SAFE-01: expired units are excluded.
    BR-02: only Accepted donations count as available stock.
    """
    today = timezone.localdate()

    total = (
        Donation.objects.filter(
            blood_group=blood_group,
            donation_status=Donation.DonationStatus.ACCEPTED,
            expiry_date__gte=today,
        ).aggregate(total=Sum("quantity_units"))["total"]
    )

    return total or 0
