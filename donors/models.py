from django.db import models

# Create your models here.
import secrets
import string

from django.core.validators import RegexValidator
from django.db import models


def generate_donor_id():
    """
    Generate a 10-character alphanumeric donor identifier.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


phone_number_validator = RegexValidator(
    regex=r"^[0-9]{1,15}$",
    message="Enter a valid phone number using digits only (maximum 15 digits).",
)


class Donor(models.Model):
    class BloodGroup(models.TextChoices):
        A_POSITIVE = "A+", "A+"
        A_NEGATIVE = "A-", "A-"
        B_POSITIVE = "B+", "B+"
        B_NEGATIVE = "B-", "B-"
        AB_POSITIVE = "AB+", "AB+"
        AB_NEGATIVE = "AB-", "AB-"
        O_POSITIVE = "O+", "O+"
        O_NEGATIVE = "O-", "O-"

    donor_id = models.CharField(
        max_length=10,
        primary_key=True,
        default=generate_donor_id,
        editable=False,
    )

    full_name = models.CharField(
        max_length=100,
    )

    date_of_birth = models.DateField()

    blood_group = models.CharField(
        max_length=3,
        choices=BloodGroup.choices,
    )

    phone_number = models.CharField(
        max_length=15,
        validators=[phone_number_validator],
    )

    email = models.EmailField(
        max_length=100,
        blank=True,
    )

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    registration_date = models.DateField(
        auto_now_add=True,
    )

    status = models.CharField(
        max_length=20,
    )

    def __str__(self):
        return f"{self.donor_id} - {self.full_name}"