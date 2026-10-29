from django import forms
from django.utils import timezone

from .models import BloodRequest


class BloodRequestForm(forms.ModelForm):
    """
    Form used by Hospital / Requesting Organization staff to submit
    a blood request (FR-6.1, FR-6.2, FR-6.7).
    """

    class Meta:
        model = BloodRequest

        fields = [
            "hospital_name",
            "patient_name",
            "blood_group",
            "units_required",
            "required_by_date",
            "reason",
        ]

        widgets = {
            "required_by_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "reason": forms.Textarea(
                attrs={"rows": 3}
            ),
            "units_required": forms.NumberInput(
                attrs={"min": 1, "max": 50}
            ),
        }

        labels = {
            "hospital_name": "Hospital / Organization",
            "patient_name": "Patient Name",
            "blood_group": "Blood Group",
            "units_required": "Units Required",
            "required_by_date": "Required By (optional)",
            "reason": "Reason / Request Details",
        }

    def clean_hospital_name(self):
        return self.cleaned_data["hospital_name"].strip()

    def clean_patient_name(self):
        return self.cleaned_data["patient_name"].strip()

    def clean_reason(self):
        return self.cleaned_data["reason"].strip()

    def clean_required_by_date(self):
        value = self.cleaned_data.get("required_by_date")

        if value and value < timezone.localdate():
            raise forms.ValidationError(
                "Required-by date cannot be in the past."
            )

        return value
    
class ReviewDecisionForm(forms.Form):
    """
    Optional note that staff can attach when approving or rejecting
    a pending request (E5-S1, FR-7.1).
    """

    note = forms.CharField(
        required=False,
        max_length=300,
        label="Note (optional)",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "e.g. reason for rejection, or handling instructions",
            }
        ),
    )

    def clean_note(self):
        return self.cleaned_data["note"].strip()
