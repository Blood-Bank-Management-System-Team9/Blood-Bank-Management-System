from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from donations.models import Donation
from donors.models import Donor
from issues.models import BloodIssueAllocation


BLOOD_GROUPS = [
    value for value, _label in Donor.BloodGroup.choices
]


def is_valid_blood_group(blood_group):
    return blood_group in BLOOD_GROUPS


def get_available_units(blood_group):
    """
    Return available units for a blood group.

    Available = accepted, non-expired donation units
                minus units already issued from those donations.
    Never returns a negative number.
    """
    if not is_valid_blood_group(blood_group):
        return 0

    today = timezone.localdate()

    donated = Donation.objects.filter(
        blood_group=blood_group,
        donation_status=Donation.DonationStatus.ACCEPTED,
        expiry_date__gte=today,
    ).aggregate(total=Sum("quantity_units"))["total"] or 0

    issued = BloodIssueAllocation.objects.filter(
        donation__blood_group=blood_group,
        donation__donation_status=Donation.DonationStatus.ACCEPTED,
        donation__expiry_date__gte=today,
    ).aggregate(total=Sum("units"))["total"] or 0

    return max(donated - issued, 0)


def get_inventory_by_blood_group():
    """Return available units for every valid blood group."""
    return {
        group: get_available_units(group)
        for group in BLOOD_GROUPS
    }


def get_near_expiry_donations():
    """Return accepted donations expiring within the next 7 days."""
    today = timezone.localdate()
    end_date = today + timedelta(days=7)

    return Donation.objects.filter(
        donation_status=Donation.DonationStatus.ACCEPTED,
        expiry_date__gte=today,
        expiry_date__lte=end_date,
    ).order_by("expiry_date")


def get_expired_donations():
    """Return accepted donations that have already expired."""
    today = timezone.localdate()

    return Donation.objects.filter(
        donation_status=Donation.DonationStatus.ACCEPTED,
        expiry_date__lt=today,
    ).order_by("expiry_date")


def get_low_stock_groups(threshold=5):
    """Return blood groups with fewer than the threshold available units."""
    inventory = get_inventory_by_blood_group()

    return {
        group: units
        for group, units in inventory.items()
        if units < threshold
    }