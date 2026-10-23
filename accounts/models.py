from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """
    Extends Django's built-in User model with a role used
    for role-based access control across the system.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrator"
        STAFF = "STAFF", "Blood Bank Staff"
        HOSPITAL = "HOSPITAL", "Hospital / Requesting Organization"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"