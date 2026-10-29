from django.contrib import admin

from .models import BloodRequest


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_id",
        "hospital_name",
        "blood_group",
        "units_required",
        "status",
        "requested_by",
        "created_at",
    )
    list_filter = ("status", "blood_group")
    search_fields = ("request_id", "hospital_name", "patient_name")
    readonly_fields = ("request_id", "created_at", "updated_at")
