from django import forms

from .models import Donation


class DonationRecordingForm(forms.ModelForm):
    class Meta:
        model = Donation

        fields = [
            "donation_date",
            "quantity_units",
            "expiry_date",
            "donation_status",
        ]

        widgets = {
            "donation_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

        labels = {
            "donation_date": "Donation Date",
            "quantity_units": "Quantity / Units",
            "expiry_date": "Expiry Date",
            "donation_status": "Donation Status",
        }