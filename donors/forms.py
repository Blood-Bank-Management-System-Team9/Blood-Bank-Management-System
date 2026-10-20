from django import forms

from .models import Donor


class DonorRegistrationForm(forms.ModelForm):
    class Meta:
        model = Donor

        fields = [
            "full_name",
            "date_of_birth",
            "blood_group",
            "phone_number",
            "email",
            "address",
            "status",
        ]

        widgets = {
            "date_of_birth": forms.DateInput(
                attrs={"type": "date"}
            ),
            "address": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

        labels = {
            "full_name": "Full Name",
            "date_of_birth": "Date of Birth",
            "blood_group": "Blood Group",
            "phone_number": "Phone Number",
            "email": "Email",
            "address": "Address",
            "status": "Status",
        }