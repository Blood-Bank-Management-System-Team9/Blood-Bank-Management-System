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
    def clean(self):
        cleaned_data = super().clean()

        donation_date = cleaned_data.get("donation_date")
        expiry_date = cleaned_data.get("expiry_date")

        if donation_date and expiry_date and expiry_date < donation_date:
            self.add_error(
                "expiry_date",
                "Expiry date cannot be before donation date."
            )

        return cleaned_data