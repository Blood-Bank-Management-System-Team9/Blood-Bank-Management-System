from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from blood_requests.models import BloodRequest
from donations.models import Donation
from donors.models import Donor
from issues.issuance import issue_blood


class ReportsTestBase(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.phone_counter = 0

        Group.objects.create(name="Blood Bank Staff")
        Group.objects.create(name="Hospital Staff")
        Group.objects.create(name="Administrator")

        self.staff_user = self.make_user("reportstaff", "Blood Bank Staff")
        self.admin_user = self.make_user("reportadmin", "Administrator")
        self.hospital_user = self.make_user("reporthospital", "Hospital Staff")

    def make_user(self, username, group_name):
        user = User.objects.create_user(username=username, password="testpass123")
        user.groups.add(Group.objects.get(name=group_name))
        return user

    def make_donation(self, blood_group, units, days_ago=0,
                      status=Donation.DonationStatus.ACCEPTED):
        self.phone_counter += 1
        donor = Donor.objects.create(
            full_name=f"Donor {self.phone_counter}",
            date_of_birth="1995-01-01",
            blood_group=blood_group,
            phone_number=f"7{self.phone_counter:09d}",
            address="Bengaluru",
        )
        donation_date = self.today - timedelta(days=days_ago)
        return Donation.objects.create(
            donor=donor,
            donation_date=donation_date,
            quantity_units=units,
            expiry_date=self.today + timedelta(days=30),
            donation_status=status,
        )

    def make_request(self, blood_group, units, status=BloodRequest.Status.APPROVED):
        return BloodRequest.objects.create(
            requested_by=self.hospital_user,
            hospital_name="City Hospital",
            patient_name="Private Patient",
            blood_group=blood_group,
            units_required=units,
            reason="Surgery",
            status=status,
        )

    def login(self, user):
        self.client.login(username=user.username, password="testpass123")


class ReportsAccessTests(ReportsTestBase):
    def test_blood_bank_staff_can_open_reports(self):
        self.login(self.staff_user)

        response = self.client.get(reverse("reports:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reports and History")

    def test_administrator_can_open_reports(self):
        self.login(self.admin_user)

        response = self.client.get(reverse("reports:home"))

        self.assertEqual(response.status_code, 200)

    def test_hospital_user_cannot_open_reports(self):
        self.login(self.hospital_user)

        response = self.client.get(reverse("reports:home"))

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("reports:home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])


class ReportsContentTests(ReportsTestBase):
    def test_summary_counts_donated_and_issued_units(self):
        self.make_donation("O+", 5)
        self.make_donation("O+", 4, status=Donation.DonationStatus.PENDING)
        blood_request = self.make_request("O+", 2)
        issue_blood(blood_request, self.staff_user)
        self.login(self.staff_user)

        response = self.client.get(reverse("reports:home"))

        summary = response.context["summary"]
        self.assertEqual(summary["units_donated"], 5)
        self.assertEqual(summary["donations_accepted"], 1)
        self.assertEqual(summary["units_issued"], 2)
        self.assertEqual(summary["issues_count"], 1)
        self.assertEqual(summary["requests_total"], 1)
        self.assertEqual(summary["requests_by_status"]["Fulfilled"], 1)

    def test_group_row_shows_current_stock_after_issue(self):
        self.make_donation("A-", 6)
        issue_blood(self.make_request("A-", 2), self.staff_user)
        self.login(self.staff_user)

        response = self.client.get(reverse("reports:home"))

        row = next(
            r for r in response.context["group_rows"]
            if r["blood_group"] == "A-"
        )
        self.assertEqual(row["donated"], 6)
        self.assertEqual(row["issued"], 2)
        self.assertEqual(row["available"], 4)

    def test_issue_history_lists_the_issue(self):
        self.make_donation("B+", 2)
        issue = issue_blood(self.make_request("B+", 1), self.staff_user)
        self.login(self.staff_user)

        response = self.client.get(reverse("reports:home"))

        self.assertIn(issue, list(response.context["issues"]))
        self.assertContains(response, issue.issue_id)

    def test_request_history_shows_status(self):
        pending = self.make_request("AB+", 1, status=BloodRequest.Status.PENDING)
        self.login(self.staff_user)

        response = self.client.get(reverse("reports:home"))

        self.assertIn(pending, list(response.context["requests"]))
        self.assertContains(response, "Pending")

    def test_patient_names_are_not_shown(self):
        self.make_request("O-", 1)
        self.login(self.staff_user)

        response = self.client.get(reverse("reports:home"))

        self.assertNotContains(response, "Private Patient")


class ReportsFilterTests(ReportsTestBase):
    def test_donations_outside_date_range_are_excluded(self):
        recent = self.make_donation("O+", 1, days_ago=2)
        old = self.make_donation("O+", 1, days_ago=60)
        self.login(self.staff_user)

        response = self.client.get(
            reverse("reports:home"),
            {
                "start_date": self.today - timedelta(days=5),
                "end_date": self.today,
            },
        )

        donations = list(response.context["donations"])
        self.assertIn(recent, donations)
        self.assertNotIn(old, donations)

    def test_blood_group_filter(self):
        op = self.make_donation("O+", 1)
        ap = self.make_donation("A+", 1)
        self.login(self.staff_user)

        response = self.client.get(
            reverse("reports:home"),
            {"blood_group": "O+"},
        )

        donations = list(response.context["donations"])
        self.assertIn(op, donations)
        self.assertNotIn(ap, donations)

    def test_request_status_filter(self):
        pending = self.make_request("O+", 1, status=BloodRequest.Status.PENDING)
        approved = self.make_request("O+", 1, status=BloodRequest.Status.APPROVED)
        self.login(self.staff_user)

        response = self.client.get(
            reverse("reports:home"),
            {"request_status": "Pending"},
        )

        requests = list(response.context["requests"])
        self.assertIn(pending, requests)
        self.assertNotIn(approved, requests)

    def test_end_date_before_start_date_shows_error(self):
        self.login(self.staff_user)

        response = self.client.get(
            reverse("reports:home"),
            {
                "start_date": self.today,
                "end_date": self.today - timedelta(days=5),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "End date must be on or after the start date")