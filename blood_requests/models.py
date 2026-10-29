import secrets
import string

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from donors.models import Donor


def generate_request_id():
    """
    Generate a 10-character alphanumeric blood request identifier.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


class BloodRequest(models.Model):
    """
    A blood request raised by an authorized requesting organization
    (E4-S2, FR-6.1 to FR-6.4, FR-6.7).

    Status flow (SAD): Pending -> Approved / Rejected -> Fulfilled.
    Approval, rejection and fulfilment are handled by E5-S1 / E5-S2.
    """

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"
        FULFILLED = "Fulfilled", "Fulfilled"

    request_id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_request_id,
        editable=False,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blood_requests",
    )

    hospital_name = models.CharField(
        max_length=150,
    )

    patient_name = models.CharField(
        max_length=100,
    )

    blood_group = models.CharField(
        max_length=3,
        choices=Donor.BloodGroup.choices,
    )

    units_required = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(50),
        ],
    )

    required_by_date = models.DateField(
        null=True,
        blank=True,
    )

    reason = models.TextField(
        max_length=500,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_blood_requests",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    review_note = models.CharField(
        max_length=300,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.request_id} - {self.blood_group} x "
            f"{self.units_required} ({self.status})"
        )
