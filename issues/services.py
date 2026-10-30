
from django.core.exceptions import ValidationError

from inventory.services import get_available_units


def validate_stock_for_issue(blood_group, requested_units):
    """
    Validate whether the requested blood units can be issued.

    Returns available units if sufficient stock exists.
    Raises ValidationError if the request is invalid
    or exceeds available stock.
    """

    if requested_units <= 0:
        raise ValidationError(
            "Requested units must be greater than zero."
        )

    available_units = get_available_units(blood_group)

    if requested_units > available_units:
        raise ValidationError(
            f"Insufficient stock. Available: {available_units} units, "
            f"Requested: {requested_units} units."
        )

    return available_units
