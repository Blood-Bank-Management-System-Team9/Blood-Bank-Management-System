"""
Role checks for blood request views.

The project currently has two role mechanisms:
- Django Groups ("Blood Bank Staff", "Hospital Staff", "Administrator"),
  used by the donor, donation, inventory and search apps.
- accounts.UserProfile.role ("STAFF", "HOSPITAL", "ADMIN"),
  used by accounts.decorators.role_required.

These helpers accept either, so blood requests work whichever one a
user account has been set up with.
"""

HOSPITAL = ("Hospital Staff", "HOSPITAL")
BLOOD_BANK_STAFF = ("Blood Bank Staff", "STAFF")
ADMINISTRATOR = ("Administrator", "ADMIN")

ALL_ROLE_GROUPS = {HOSPITAL[0], BLOOD_BANK_STAFF[0], ADMINISTRATOR[0]}


def user_has_role(user, *roles):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    group_names = [group_name for group_name, _profile_role in roles]
    profile_roles = [profile_role for _group_name, profile_role in roles]

    user_groups = set(user.groups.values_list("name", flat=True))

    if user_groups.intersection(group_names):
        return True

    # A user who belongs to any role group is decided by groups alone.
    # Every account gets a UserProfile automatically (default role STAFF),
    # so that default must not grant staff powers to, for example,
    # a Hospital Staff user.
    if user_groups.intersection(ALL_ROLE_GROUPS):
        return False

    # No role group at all: fall back to accounts.UserProfile.role.
    profile = getattr(user, "profile", None)

    return profile is not None and profile.role in profile_roles


def can_submit_request(user):
    """
    FR-6.1: an authorized requesting organization submits requests.
    """
    return user_has_role(user, HOSPITAL)


def can_review_request(user):
    """
    FR-7.1: only authorized Blood Bank Staff approve or reject requests.
    """
    return user_has_role(user, BLOOD_BANK_STAFF)