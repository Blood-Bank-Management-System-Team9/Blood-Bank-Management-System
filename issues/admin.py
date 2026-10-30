from django.contrib import admin

from .models import BloodIssue, BloodIssueAllocation


class BloodIssueAllocationInline(admin.TabularInline):
    model = BloodIssueAllocation
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BloodIssue)
class BloodIssueAdmin(admin.ModelAdmin):
    """
    Issues are an audit trail: they are created only through the issue
    workflow, so the admin is read-only.
    """

    list_display = (
        "issue_id",
        "blood_request",
        "blood_group",
        "units_issued",
        "issued_by",
        "issued_at",
    )
    list_filter = ("blood_group",)
    search_fields = ("issue_id", "blood_request__request_id")
    readonly_fields = (
        "issue_id",
        "blood_request",
        "blood_group",
        "units_issued",
        "issued_by",
        "issued_at",
    )
    inlines = [BloodIssueAllocationInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False