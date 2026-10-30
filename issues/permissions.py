from blood_requests.permissions import can_review_request


def can_issue_blood(user):
    """
    Only Blood Bank Staff issue blood. Same rule as approving requests.
    """
    return can_review_request(user)