"""
Availability lookups used by the Blood Availability Search (E4-S1).

get_available_units is re-exported from inventory.services, the single
source of truth. That way the search also sees units already issued.
The view and tests keep their existing imports from this module.
"""

from donors.models import Donor
from inventory.services import get_available_units


BLOOD_GROUPS = [value for value, _label in Donor.BloodGroup.choices]


def is_valid_blood_group(blood_group):
    return blood_group in BLOOD_GROUPS


__all__ = [
    "BLOOD_GROUPS",
    "get_available_units",
    "is_valid_blood_group",
]