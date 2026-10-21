import secrets
import string

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from donors.models import Donor


def generate_donation_id():
    """
    Generate a 10-character alphanumeric donation identifier.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


def validate_donation_date(value):
    """
    A donation date cannot be in the future.
    """
    if value > timezone.localdate():
        raise ValidationError("Donation date cannot be in the future.")


class Donation(models.Model):
    class DonationStatus(models.TextChoices):
        PENDING = "Pending", "Pending"
        ACCEPTED = "Accepted", "Accepted"
        REJECTED = "Rejected", "Rejected"

    donation_id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_donation_id,
        editable=False,
    )

    donor = models.ForeignKey(
        Donor,
        on_delete=models.PROTECT,
    )

    donation_date = models.DateField(
        validators=[validate_donation_date],
    )

    blood_group = models.CharField(
        max_length=3,
        choices=Donor.BloodGroup.choices,
        editable=False,
    )

    quantity_units = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    expiry_date = models.DateField()

    donation_status = models.CharField(
        max_length=20,
        choices=DonationStatus.choices,
    )

    def save(self, *args, **kwargs):
        self.blood_group = self.donor.blood_group
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.donation_id} - {self.donor.full_name}"