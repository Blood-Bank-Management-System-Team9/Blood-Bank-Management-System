from django import forms
from django.core.exceptions import ValidationError

from blood_requests.models import BloodRequest
from donations.models import Donation
from donors.models import Donor


BLOOD_GROUP_CHOICES = [("", "All blood groups")] + list(Donor.BloodGroup.choices)
REQUEST_STATUS_CHOICES = [("", "All statuses")] + list(BloodRequest.Status.choices)
DONATION_STATUS_CHOICES = [("", "All statuses")] + list(Donation.DonationStatus.choices)


class ReportFilterForm(forms.Form):
    """
    Filters for the reports page. Blank values mean "no filter" (or the
    default date range, handled in reports/views.py).
    """

    start_date = forms.DateField(
        required=False,
        label="From",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    end_date = forms.DateField(
        required=False,
        label="To",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    blood_group = forms.ChoiceField(
        required=False,
        choices=BLOOD_GROUP_CHOICES,
        label="Blood group",
    )

    donation_status = forms.ChoiceField(
        required=False,
        choices=DONATION_STATUS_CHOICES,
        label="Donation status",
    )

    request_status = forms.ChoiceField(
        required=False,
        choices=REQUEST_STATUS_CHOICES,
        label="Request status",
    )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")

        if start and end and end < start:
            raise ValidationError("End date must be on or after the start date.")

        return cleaned