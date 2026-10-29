from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile

from .models import BloodRequest


class SubmitBloodRequestTests(TestCase):
    def setUp(self):
        self.url = reverse("blood_requests:submit")

        self.hospital_group = Group.objects.create(name="Hospital Staff")
        self.staff_group = Group.objects.create(name="Blood Bank Staff")

        self.hospital_user = User.objects.create_user(
            username="hospital1",
            password="testpass123",
        )
        self.hospital_user.groups.add(self.hospital_group)

        self.staff_user = User.objects.create_user(
            username="bloodstaff",
            password="testpass123",
        )
        self.staff_user.groups.add(self.staff_group)

        self.valid_data = {
            "hospital_name": "City Hospital",
            "patient_name": "Anita Rao",
            "blood_group": "A+",
            "units_required": 2,
            "required_by_date": "",
            "reason": "Surgery",
        }

    def login_hospital(self):
        self.client.login(username="hospital1", password="testpass123")

    def test_valid_request_is_created_as_pending(self):
        """
        TC-REQ-01 (submit part) / FR-6.1 - FR-6.4:
        A valid request is created with a unique ID, status Pending,
        and is linked to the submitting user.
        """
        self.login_hospital()

        response = self.client.post(self.url, self.valid_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BloodRequest.objects.count(), 1)

        blood_request = BloodRequest.objects.get()

        self.assertEqual(blood_request.status, BloodRequest.Status.PENDING)
        self.assertEqual(blood_request.blood_group, "A+")
        self.assertEqual(blood_request.units_required, 2)
        self.assertEqual(blood_request.requested_by, self.hospital_user)
        self.assertEqual(len(blood_request.request_id), 10)
        self.assertContains(response, blood_request.request_id)
        self.assertContains(response, "Status: Pending")

    def test_each_request_gets_a_unique_id(self):
        """
        FR-6.3 / DR-04: each request is uniquely identified.
        """
        self.login_hospital()

        self.client.post(self.url, self.valid_data)
        self.client.post(self.url, self.valid_data)

        ids = list(BloodRequest.objects.values_list("request_id", flat=True))

        self.assertEqual(len(ids), 2)
        self.assertNotEqual(ids[0], ids[1])

    def test_missing_units_is_rejected(self):
        """
        TC-REQ-02 / FR-6.7 / FR-6.2:
        Units left empty -> request is NOT created and a
        'required' message is shown.
        """
        self.login_hospital()

        data = dict(self.valid_data, units_required="")

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BloodRequest.objects.count(), 0)
        self.assertContains(response, "This field is required.")

    def test_missing_blood_group_is_rejected(self):
        """
        FR-6.7 / FR-6.2: blood group is mandatory.
        """
        self.login_hospital()

        data = dict(self.valid_data, blood_group="")

        response = self.client.post(self.url, data)

        self.assertEqual(BloodRequest.objects.count(), 0)
        self.assertTrue(response.context["form"].errors.get("blood_group"))

    def test_invalid_blood_group_is_rejected(self):
        """
        DR-01: only standard blood groups are accepted.
        """
        self.login_hospital()

        data = dict(self.valid_data, blood_group="XYZ")

        self.client.post(self.url, data)

        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_zero_units_is_rejected(self):
        """
        Boundary: at least 1 unit must be requested.
        """
        self.login_hospital()

        data = dict(self.valid_data, units_required=0)

        response = self.client.post(self.url, data)

        self.assertEqual(BloodRequest.objects.count(), 0)
        self.assertTrue(response.context["form"].errors.get("units_required"))

    def test_past_required_by_date_is_rejected(self):
        """
        A required-by date in the past is not accepted.
        """
        self.login_hospital()

        yesterday = timezone.localdate() - timedelta(days=1)
        data = dict(self.valid_data, required_by_date=yesterday.isoformat())

        response = self.client.post(self.url, data)

        self.assertEqual(BloodRequest.objects.count(), 0)
        self.assertContains(response, "Required-by date cannot be in the past.")

    def test_blood_group_is_prefilled_from_search(self):
        """
        Coming from Blood Search (?blood_group=O+) pre-selects the group.
        """
        self.login_hospital()

        response = self.client.get(self.url, {"blood_group": "O+"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["blood_group"], "O+")

    def test_hospital_role_via_user_profile_can_submit(self):
        """
        Users set up with accounts.UserProfile role HOSPITAL
        (instead of the Hospital Staff group) can also submit.
        """
        user = User.objects.create_user(username="hosp2", password="testpass123")
        user.profile.role = UserProfile.Role.HOSPITAL
        user.profile.save()

        self.client.login(username="hosp2", password="testpass123")

        self.client.post(self.url, self.valid_data)

        self.assertEqual(BloodRequest.objects.count(), 1)

    def test_unauthenticated_user_is_redirected(self):
        """
        TC-SEC-01 (request part) / SEC-01.
        """
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_blood_bank_staff_cannot_submit_requests(self):
        """
        FR-6.1 / SEC-02: only requesting organizations submit requests.
        """
        self.client.login(username="bloodstaff", password="testpass123")

        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_post_without_csrf_token_is_rejected(self):
        """
        TC-SEC-06 (request part) / SEC-07:
        POST without a CSRF token is rejected and no request is created.
        """
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="hospital1", password="testpass123")

        response = csrf_client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(BloodRequest.objects.count(), 0)

    def test_sql_injection_text_is_stored_as_plain_text(self):
        """
        TC-SEC-06 (request part) / SEC-08:
        Injection payloads are treated as plain text.
        """
        self.login_hospital()

        payload = "' OR '1'='1"
        data = dict(self.valid_data, patient_name=payload)

        self.client.post(self.url, data)

        self.assertEqual(BloodRequest.objects.count(), 1)
        self.assertEqual(BloodRequest.objects.get().patient_name, payload)

class ReviewBloodRequestTests(TestCase):
    """
    E5-S1 (FR-7.1): Blood Bank Staff open a pending request and
    approve or reject it. The status changes accordingly.
    """

    def setUp(self):
        self.hospital_group = Group.objects.create(name="Hospital Staff")
        self.staff_group = Group.objects.create(name="Blood Bank Staff")

        self.hospital_user = User.objects.create_user(
            username="hospital1",
            password="testpass123",
        )
        self.hospital_user.groups.add(self.hospital_group)

        self.staff_user = User.objects.create_user(
            username="bloodstaff",
            password="testpass123",
        )
        self.staff_user.groups.add(self.staff_group)

        self.blood_request = BloodRequest.objects.create(
            requested_by=self.hospital_user,
            hospital_name="City Hospital",
            patient_name="Anita Rao",
            blood_group="A+",
            units_required=2,
            reason="Surgery",
        )

        self.pending_url = reverse("blood_requests:pending")
        self.detail_url = reverse(
            "blood_requests:detail",
            args=[self.blood_request.request_id],
        )

    def login_staff(self):
        self.client.login(username="bloodstaff", password="testpass123")

    def login_hospital(self):
        self.client.login(username="hospital1", password="testpass123")

    # ---- opening pending requests ----

    def test_staff_sees_pending_request_in_list(self):
        self.login_staff()

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.blood_request.request_id)
        self.assertContains(response, "City Hospital")

    def test_staff_can_open_request_details(self):
        self.login_staff()

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Anita Rao")
        self.assertContains(response, "Surgery")
        self.assertContains(response, "Approve")
        self.assertContains(response, "Reject")

    def test_unknown_request_returns_404(self):
        self.login_staff()

        response = self.client.get(
            reverse("blood_requests:detail", args=["NOSUCHID12"])
        )

        self.assertEqual(response.status_code, 404)

    def test_opening_details_does_not_change_status(self):
        self.login_staff()

        self.client.get(self.detail_url)

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.PENDING,
        )

    # ---- approve ----

    def test_staff_can_approve_request(self):
        self.login_staff()

        response = self.client.post(
            self.detail_url,
            {"decision": "approve", "note": "Stock checked"},
        )

        self.assertRedirects(response, self.pending_url)

        self.blood_request.refresh_from_db()

        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.APPROVED,
        )
        self.assertEqual(self.blood_request.reviewed_by, self.staff_user)
        self.assertIsNotNone(self.blood_request.reviewed_at)
        self.assertEqual(self.blood_request.review_note, "Stock checked")

    def test_approved_request_leaves_pending_list(self):
        self.login_staff()

        self.client.post(self.detail_url, {"decision": "approve"})

        response = self.client.get(self.pending_url)

        self.assertNotIn(
            self.blood_request,
            list(response.context["pending_requests"]),
        )
        self.assertContains(response, "There are no pending blood requests")

    # ---- reject ----

    def test_staff_can_reject_request(self):
        self.login_staff()

        response = self.client.post(
            self.detail_url,
            {"decision": "reject", "note": "Duplicate request"},
        )

        self.assertRedirects(response, self.pending_url)

        self.blood_request.refresh_from_db()

        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.REJECTED,
        )
        self.assertEqual(self.blood_request.reviewed_by, self.staff_user)
        self.assertEqual(self.blood_request.review_note, "Duplicate request")

    # ---- status rules ----

    def test_request_cannot_be_reviewed_twice(self):
        self.login_staff()

        self.client.post(self.detail_url, {"decision": "approve"})

        response = self.client.post(
            self.detail_url,
            {"decision": "reject"},
            follow=True,
        )

        self.assertContains(response, "has already been reviewed")

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.APPROVED,
        )

    def test_invalid_decision_changes_nothing(self):
        self.login_staff()

        response = self.client.post(self.detail_url, {"decision": "maybe"})

        self.assertEqual(response.status_code, 200)

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.PENDING,
        )

    def test_missing_decision_changes_nothing(self):
        self.login_staff()

        self.client.post(self.detail_url, {"note": "no button pressed"})

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.PENDING,
        )

    # ---- access control ----

    def test_hospital_user_cannot_open_pending_list(self):
        self.login_hospital()

        response = self.client.get(self.pending_url)

        self.assertEqual(response.status_code, 403)

    def test_hospital_user_cannot_open_details(self):
        self.login_hospital()

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 403)

    def test_hospital_user_cannot_approve_own_request(self):
        self.login_hospital()

        response = self.client.post(self.detail_url, {"decision": "approve"})

        self.assertEqual(response.status_code, 403)

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.PENDING,
        )

    def test_staff_role_via_user_profile_can_review(self):
        """
        Users set up with accounts.UserProfile role STAFF
        (instead of the Blood Bank Staff group) can also review.
        """
        user = User.objects.create_user(
            username="staff2",
            password="testpass123",
        )
        user.profile.role = UserProfile.Role.STAFF
        user.profile.save()

        self.client.login(username="staff2", password="testpass123")

        self.client.post(self.detail_url, {"decision": "approve"})

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.APPROVED,
        )

    def test_unauthenticated_user_is_redirected_to_login(self):
        response = self.client.post(self.detail_url, {"decision": "approve"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.PENDING,
        )

    def test_review_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="bloodstaff", password="testpass123")

        response = csrf_client.post(self.detail_url, {"decision": "approve"})

        self.assertEqual(response.status_code, 403)

        self.blood_request.refresh_from_db()
        self.assertEqual(
            self.blood_request.status,
            BloodRequest.Status.PENDING,
        )