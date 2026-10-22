from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from donations.models import Donation
from donors.models import Donor

from .services import get_available_units


class BloodAvailabilitySearchTests(TestCase):
    def setUp(self):
        self.url = reverse("blood_search:availability")
        self.today = timezone.localdate()

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

        self.no_role_user = User.objects.create_user(
            username="norole",
            password="testpass123",
        )

        self.donor_o_pos = self.create_donor("O+", "9000000001")
        self.donor_a_neg = self.create_donor("A-", "9000000002")

    def create_donor(self, blood_group, phone_number):
        return Donor.objects.create(
            full_name=f"Donor {blood_group}",
            date_of_birth="1998-05-12",
            blood_group=blood_group,
            phone_number=phone_number,
            address="Bengaluru",
        )

    def create_donation(self, donor, units, status, expiry_offset_days):
        return Donation.objects.create(
            donor=donor,
            donation_date=self.today,
            quantity_units=units,
            expiry_date=self.today + timedelta(days=expiry_offset_days),
            donation_status=status,
        )

    def test_search_available_blood_group(self):
        """
        TC-SRCH-01:
        O+ has 5 valid units and 1 expired unit. Search shows
        O+ as Available with quantity 5 (expired unit not counted).
        """
        self.create_donation(self.donor_o_pos, 3, "Accepted", 20)
        self.create_donation(self.donor_o_pos, 2, "Accepted", 10)
        self.create_donation(self.donor_o_pos, 1, "Accepted", -1)

        self.client.login(username="hospital1", password="testpass123")

        response = self.client.get(self.url, {"blood_group": "O+"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result"]["available_units"], 5)
        self.assertTrue(response.context["result"]["is_available"])
        self.assertContains(response, "Available")

    def test_search_unavailable_blood_group(self):
        """
        TC-SRCH-02:
        AB- has 0 valid units. Search shows a clear
        'AB- is currently unavailable' message with quantity 0.
        """
        self.client.login(username="hospital1", password="testpass123")

        response = self.client.get(self.url, {"blood_group": "AB-"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result"]["available_units"], 0)
        self.assertFalse(response.context["result"]["is_available"])
        self.assertContains(response, "AB- is currently unavailable.")

    def test_expired_units_excluded_from_availability(self):
        """
        TC-MON-01 (search part) / FR-5.3 / SAFE-01:
        A- has one unit expired yesterday and one expiring in
        20 days. Availability for A- is 1.
        """
        self.create_donation(self.donor_a_neg, 1, "Accepted", -1)
        self.create_donation(self.donor_a_neg, 1, "Accepted", 20)

        self.assertEqual(get_available_units("A-"), 1)

    def test_only_accepted_donations_are_counted(self):
        """
        BR-02: Pending and Rejected donations are not available stock.
        """
        self.create_donation(self.donor_o_pos, 2, "Accepted", 20)
        self.create_donation(self.donor_o_pos, 4, "Pending", 20)
        self.create_donation(self.donor_o_pos, 3, "Rejected", 20)

        self.assertEqual(get_available_units("O+"), 2)

    def test_unit_expiring_today_is_still_available(self):
        """
        Boundary: a unit whose expiry date is today has not expired yet.
        """
        self.create_donation(self.donor_o_pos, 1, "Accepted", 0)

        self.assertEqual(get_available_units("O+"), 1)

    def test_blood_bank_staff_can_search(self):
        """
        FR-5.1: Blood Bank Staff are authorized users.
        """
        self.client.login(username="bloodstaff", password="testpass123")

        response = self.client.get(self.url, {"blood_group": "O+"})

        self.assertEqual(response.status_code, 200)

    def test_page_loads_without_search(self):
        """
        Opening the page without choosing a group shows the form only.
        """
        self.client.login(username="hospital1", password="testpass123")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["result"])

    def test_invalid_blood_group_shows_error(self):
        """
        Invalid input is rejected with a message and no result.
        """
        self.client.login(username="hospital1", password="testpass123")

        response = self.client.get(self.url, {"blood_group": "XYZ"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["result"])
        self.assertContains(response, "Please select a valid blood group.")

    def test_unauthenticated_user_is_redirected(self):
        """
        TC-SEC-01 (search part) / SEC-01:
        Unauthenticated access is redirected to login.
        """
        response = self.client.get(self.url, {"blood_group": "O+"})

        self.assertEqual(response.status_code, 302)

    def test_user_without_role_is_forbidden(self):
        """
        SEC-02: A logged-in user with no BBMS role cannot search.
        """
        self.client.login(username="norole", password="testpass123")

        response = self.client.get(self.url, {"blood_group": "O+"})

        self.assertEqual(response.status_code, 403)
