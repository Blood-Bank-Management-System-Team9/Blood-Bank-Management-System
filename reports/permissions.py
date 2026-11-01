from blood_requests.permissions import ADMINISTRATOR, BLOOD_BANK_STAFF, user_has_role


def can_view_reports(user):
    """
    E5-S3: Blood Bank Staff and Administrators can view reports and history.
    Hospital users cannot.
    """
    return user_has_role(user, BLOOD_BANK_STAFF, ADMINISTRATOR)