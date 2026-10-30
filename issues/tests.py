import json
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from blood_requests.models import BloodRequest
from blood_search.services import get_available_units as search_available_units
from donations.models import Donation
from donors.models import Donor
from inventory.services import get_available_units

from .issuance import InsufficientStock, RequestNotApproved, issue_blood
from .models import BloodIssue, BloodIssueAllocation


class BloodIssueTestBase(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.phone_counter = 0

        staff_group = Group.objects.create(name="Blood Bank Staff")
        hospital_group = Group.objects.create(name="Hospital Staff")

        self.staff_user = User.objects.create_user(
            username="issuestaff",
            password="testpass123",
        )
        self.staff_user.groups.add(staff_group)

        self.hospital_user = User.objects.create_user(
            username="issuehospital",
            password="testpass123",
        )
        self.hospital_user.groups.add(hospital_group)

    def make_donation(self, blood_group, units, expiry_offset_days,
                      status=Donation.DonationStatus.ACCEPTED):
        self.phone_counter += 1
        donor = Donor.objects.create(
            full_name=f"Donor {self.phone_counter}",
            date_of_birth="1995-01-01",
            blood_group=blood_group,
            phone_number=f"8{self.phone_counter:09d}",
            address="Bengaluru",
        )
        return Donation.objects.create(
            donor=donor,
            donation_date=self.today,
            quantity_units=units,
            expiry_date=self.today + timedelta(days=expiry_offset_days),
            donation_status=status,
        )

    def make_request(self, blood_group, units, status=BloodRequest.Status.APPROVED):
        return BloodRequest.objects.create(
            requested_by=self.hospital_user,
            hospital_name="City Hospital",
            patient_name="Test Patient",
            blood_group=blood_group,
            units_required=units,
            reason="Surgery",
            status=status,
        )


class IssueBloodServiceTests(BloodIssueTestBase):
    """E5-S2 / E3-S4: issuing reduces stock and never makes it negative."""

    def test_issue_reduces_available_stock(self):
        self.make_donation("O+", 5, 10)
        blood_request = self.make_request("O+", 2)

        issue_blood(blood_request, self.staff_user)

        self.assertEqual(get_available_units("O+"), 3)

    def test_issue_marks_request_fulfilled(self):
        self.make_donation("O+", 5, 10)
        blood_request = self.make_request("O+", 2)

        issue_blood(blood_request, self.staff_user)

        blood_request.refresh_from_db()
        self.assertEqual(blood_request.status, BloodRequest.Status.FULFILLED)

    def test_issue_records_who_issued_it(self):
        self.make_donation("O+", 5, 10)
        blood_request = self.make_request("O+", 2)

        issue = issue_blood(blood_request, self.staff_user)

        self.assertEqual(issue.issued_by, self.staff_user)
        self.assertEqual(issue.units_issued, 2)
        self.assertEqual(issue.blood_group, "O+")

    def test_units_come_from_soonest_expiring_batch_first(self):
        late_batch = self.make_donation("A+", 5, 30)
        early_batch = self.make_donation("A+", 2, 5)
        blood_request = self.make_request("A+", 3)

        issue = issue_blood(blood_request, self.staff_user)

        taken = {
            allocation.donation_id: allocation.units
            for allocation in BloodIssueAllocation.objects.filter(issue=issue)
        }
        self.assertEqual(taken, {early_batch.pk: 2, late_batch.pk: 1})

    def test_expired_units_are_never_issued(self):
        self.make_donation("B+", 10, -1)
        self.make_donation("B+", 1, 10)
        blood_request = self.make_request("B+", 2)

        with self.assertRaises(InsufficientStock):
            issue_blood(blood_request, self.staff_user)

    def test_insufficient_stock_changes_nothing(self):
        self.make_donation("AB-", 1, 10)
        blood_request = self.make_request("AB-", 2)

        with self.assertRaises(InsufficientStock):
            issue_blood(blood_request, self.staff_user)

        blood_request.refresh_from_db()
        self.assertEqual(blood_request.status, BloodRequest.Status.APPROVED)
        self.assertFalse(BloodIssue.objects.filter(blood_request=blood_request).exists())
        self.assertEqual(get_available_units("AB-"), 1)

    def test_stock_never_goes_negative_across_issues(self):
        self.make_donation("O-", 5, 10)
        first = self.make_request("O-", 3)
        second = self.make_request("O-", 3)

        issue_blood(first, self.staff_user)

        with self.assertRaises(InsufficientStock):
            issue_blood(second, self.staff_user)

        self.assertEqual(get_available_units("O-"), 2)

    def test_cannot_issue_the_same_request_twice(self):
        self.make_donation("O+", 5, 10)
        blood_request = self.make_request("O+", 2)

        issue_blood(blood_request, self.staff_user)

        with self.assertRaises(RequestNotApproved):
            issue_blood(blood_request, self.staff_user)

        self.assertEqual(BloodIssue.objects.filter(blood_request=blood_request).count(), 1)
        self.assertEqual(get_available_units("O+"), 3)

    def test_pending_request_cannot_be_issued(self):
        self.make_donation("O+", 5, 10)
        blood_request = self.make_request("O+", 2, status=BloodRequest.Status.PENDING)

        with self.assertRaises(RequestNotApproved):
            issue_blood(blood_request, self.staff_user)

        self.assertEqual(get_available_units("O+"), 5)

    def test_rejected_request_cannot_be_issued(self):
        self.make_donation("O+", 5, 10)
        blood_request = self.make_request("O+", 2, status=BloodRequest.Status.REJECTED)

        with self.assertRaises(RequestNotApproved):
            issue_blood(blood_request, self.staff_user)

        self.assertEqual(get_available_units("O+"), 5)

    def test_pending_donations_are_not_issued(self):
        self.make_donation("O+", 4, 10, status=Donation.DonationStatus.PENDING)
        blood_request = self.make_request("O+", 1)

        with self.assertRaises(InsufficientStock):
            issue_blood(blood_request, self.staff_user)


class BloodSearchReflectsIssuedStockTests(BloodIssueTestBase):
    """Regression: blood search must not show blood that was already issued."""

    def test_blood_search_stock_drops_after_issue(self):
        self.make_donation("A-", 4, 10)
        blood_request = self.make_request("A-", 3)

        self.assertEqual(search_available_units("A-"), 4)

        issue_blood(blood_request, self.staff_user)

        self.assertEqual(search_available_units("A-"), 1)


class IssueViewTests(BloodIssueTestBase):
    def setUp(self):
        super().setUp()
        self.make_donation("O+", 5, 10)
        self.blood_request = self.make_request("O+", 2)
        self.issue_url = reverse("issues:issue", args=[self.blood_request.request_id])

    def login_staff(self):
        self.client.login(username="issuestaff", password="testpass123")

    def login_hospital(self):
        self.client.login(username="issuehospital", password="testpass123")

    def test_staff_can_open_issue_page(self):
        self.login_staff()

        response = self.client.get(self.issue_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Issue 2 unit(s)")

    def test_opening_issue_page_does_not_issue_blood(self):
        self.login_staff()

        self.client.get(self.issue_url)

        self.blood_request.refresh_from_db()
        self.assertEqual(self.blood_request.status, BloodRequest.Status.APPROVED)
        self.assertEqual(get_available_units("O+"), 5)

    def test_staff_post_issues_blood_and_redirects(self):
        self.login_staff()

        response = self.client.post(self.issue_url)

        self.assertRedirects(response, self.issue_url)

        self.blood_request.refresh_from_db()
        self.assertEqual(self.blood_request.status, BloodRequest.Status.FULFILLED)
        self.assertEqual(get_available_units("O+"), 3)

    def test_post_for_pending_request_shows_error_and_issues_nothing(self):
        self.login_staff()
        pending = self.make_request("O+", 1, status=BloodRequest.Status.PENDING)
        url = reverse("issues:issue", args=[pending.request_id])

        response = self.client.post(url, follow=True)

        self.assertContains(response, "is not Approved")
        self.assertFalse(BloodIssue.objects.filter(blood_request=pending).exists())

    def test_hospital_user_cannot_open_issue_page(self):
        self.login_hospital()

        response = self.client.get(self.issue_url)

        self.assertEqual(response.status_code, 403)

    def test_hospital_user_cannot_issue_blood(self):
        self.login_hospital()

        response = self.client.post(self.issue_url)

        self.assertEqual(response.status_code, 403)
        self.blood_request.refresh_from_db()
        self.assertEqual(self.blood_request.status, BloodRequest.Status.APPROVED)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.post(self.issue_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_issue_page_shows_batches_after_issue(self):
        self.login_staff()
        self.client.post(self.issue_url)

        response = self.client.get(self.issue_url)

        self.assertContains(response, "Taken From")
        self.assertContains(response, "Issue Record")


class IssueApiTests(BloodIssueTestBase):
    """
    POST /api/issues (SAD: direct issuing endpoint, TC-ISS-02 / TC-SEC-02).
    Same rules as the issue page.
    """

    def setUp(self):
        super().setUp()
        self.make_donation("O+", 5, 10)
        self.blood_request = self.make_request("O+", 2)

    def login_staff(self):
        self.client.login(username="issuestaff", password="testpass123")

    def login_hospital(self):
        self.client.login(username="issuehospital", password="testpass123")

    def test_route_is_exactly_api_issues(self):
        self.assertEqual(reverse("api-issues"), "/api/issues")

    def test_anonymous_user_gets_401_and_nothing_is_issued(self):
        response = self.client.post(
            reverse("api-issues"),
            {"request_id": self.blood_request.request_id},
        )

        self.assertEqual(response.status_code, 401)
        self.blood_request.refresh_from_db()
        self.assertEqual(self.blood_request.status, BloodRequest.Status.APPROVED)

    def test_hospital_user_gets_403_and_nothing_is_issued(self):
        self.login_hospital()

        response = self.client.post(
            reverse("api-issues"),
            {"request_id": self.blood_request.request_id},
        )

        self.assertEqual(response.status_code, 403)
        self.blood_request.refresh_from_db()
        self.assertEqual(self.blood_request.status, BloodRequest.Status.APPROVED)
        self.assertEqual(get_available_units("O+"), 5)

    def test_get_is_not_allowed(self):
        self.login_staff()

        response = self.client.get(reverse("api-issues"))

        self.assertEqual(response.status_code, 405)

    def test_staff_can_issue_with_form_data(self):
        self.login_staff()

        response = self.client.post(
            reverse("api-issues"),
            {"request_id": self.blood_request.request_id},
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["request_id"], self.blood_request.request_id)
        self.assertEqual(body["units_issued"], 2)
        self.assertEqual(body["blood_group"], "O+")
        self.assertTrue(body["issue_id"])

        self.blood_request.refresh_from_db()
        self.assertEqual(self.blood_request.status, BloodRequest.Status.FULFILLED)
        self.assertEqual(get_available_units("O+"), 3)

    def test_staff_can_issue_with_json_body(self):
        self.login_staff()

        response = self.client.post(
            reverse("api-issues"),
            data=json.dumps({"request_id": self.blood_request.request_id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(get_available_units("O+"), 3)

    def test_missing_request_id_returns_400(self):
        self.login_staff()

        response = self.client.post(reverse("api-issues"), {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "request_id_required")

    def test_unknown_request_returns_404(self):
        self.login_staff()

        response = self.client.post(
            reverse("api-issues"),
            {"request_id": "NOSUCHID12"},
        )

        self.assertEqual(response.status_code, 404)

    def test_pending_request_returns_409_and_issues_nothing(self):
        self.login_staff()
        pending = self.make_request("O+", 1, status=BloodRequest.Status.PENDING)

        response = self.client.post(
            reverse("api-issues"),
            {"request_id": pending.request_id},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "request_not_approved")
        self.assertFalse(BloodIssue.objects.filter(blood_request=pending).exists())

    def test_insufficient_stock_returns_409_and_request_stays_approved(self):
        self.login_staff()
        big = self.make_request("O+", 10)

        response = self.client.post(
            reverse("api-issues"),
            {"request_id": big.request_id},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "insufficient_stock")
        big.refresh_from_db()
        self.assertEqual(big.status, BloodRequest.Status.APPROVED)
        self.assertEqual(get_available_units("O+"), 5)

    def test_second_post_for_same_request_returns_409(self):
        self.login_staff()
        url = reverse("api-issues")

        first = self.client.post(url, {"request_id": self.blood_request.request_id})
        second = self.client.post(url, {"request_id": self.blood_request.request_id})

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            BloodIssue.objects.filter(blood_request=self.blood_request).count(),
            1,
        )

    def test_session_post_without_csrf_token_is_rejected(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.login(username="issuestaff", password="testpass123")

        response = csrf_client.post(
            reverse("api-issues"),
            {"request_id": self.blood_request.request_id},
        )

        self.assertEqual(response.status_code, 403)
        self.blood_request.refresh_from_db()
        self.assertEqual(self.blood_request.status, BloodRequest.Status.APPROVED)