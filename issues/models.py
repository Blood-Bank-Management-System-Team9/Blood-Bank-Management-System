import secrets
import string

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from blood_requests.models import BloodRequest
from donations.models import Donation
from donors.models import Donor


def generate_issue_id():
    """
    Generate a 10-character alphanumeric blood issue identifier.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


class BloodIssue(models.Model):
    """
    Record of blood issued against one approved blood request (E5-S2).

    Created together with its BloodIssueAllocation rows inside a single
    database transaction (see issues/issuance.py).
    """

    issue_id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_issue_id,
        editable=False,
    )

    blood_request = models.OneToOneField(
        BloodRequest,
        on_delete=models.PROTECT,
        related_name="issue",
    )

    blood_group = models.CharField(
        max_length=3,
        choices=Donor.BloodGroup.choices,
    )

    units_issued = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blood_issues",
    )

    issued_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.issue_id} - {self.blood_group} x {self.units_issued}"


class BloodIssueAllocation(models.Model):
    """
    Which donation batch the issued units came from.

    Available stock = accepted, unexpired donation units minus the units
    allocated here (see inventory.services.get_available_units).
    """

    issue = models.ForeignKey(
        BloodIssue,
        on_delete=models.CASCADE,
        related_name="allocations",
    )

    donation = models.ForeignKey(
        Donation,
        on_delete=models.PROTECT,
        related_name="issue_allocations",
    )

    units = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    def __str__(self):
        return f"{self.issue.issue_id}: {self.units} unit(s) from {self.donation_id}"
