
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from donors.models import Donor
from .models import Donation
from inventory.services import get_available_units


class DonationHistoryLinkTests(TestCase):
    def test_donation_is_linked_to_correct_donor(self):
        donor = Donor.objects.create(
            full_name="Ravi Kumar",
            date_of_birth=date(1998, 5, 12),
            blood_group=Donor.BloodGroup.O_POSITIVE,
            phone_number="9876543210",
            address="Bengaluru",
        )

        donation = Donation.objects.create(
            donor=donor,
            donation_date=timezone.localdate(),
            quantity_units=1,
            expiry_date=timezone.localdate() + timedelta(days=30),
            donation_status=Donation.DonationStatus.ACCEPTED,
        )

        self.assertEqual(donation.donor, donor)

        self.assertTrue(
            donor.donation_set.filter(
                donation_id=donation.donation_id
            ).exists()
        )

        linked_donation = donor.donation_set.get(
            donation_id=donation.donation_id
        )

        self.assertEqual(linked_donation.blood_group, donor.blood_group)
        self.assertEqual(linked_donation.quantity_units, 1)
        self.assertEqual(
            linked_donation.donation_status,
            Donation.DonationStatus.ACCEPTED,
        )

    def test_accepted_donation_details_are_available_for_inventory(self):
        donor = Donor.objects.create(
            full_name="Ravi Kumar",
            date_of_birth=date(1998, 5, 12),
            blood_group=Donor.BloodGroup.O_POSITIVE,
            phone_number="9876543210",
        )

        donation = Donation.objects.create(
            donor=donor,
            donation_date=timezone.localdate(),
            quantity_units=1,
            expiry_date=timezone.localdate() + timedelta(days=30),
            donation_status=Donation.DonationStatus.ACCEPTED,
        )

        accepted_donation = Donation.objects.get(
            donation_id=donation.donation_id,
            donation_status=Donation.DonationStatus.ACCEPTED,
        )

        self.assertEqual(
            accepted_donation.blood_group,
            Donor.BloodGroup.O_POSITIVE,
        )
        self.assertEqual(accepted_donation.quantity_units, 1)
        self.assertEqual(
            accepted_donation.donation_date,
            donation.donation_date,
        )
        self.assertEqual(
            accepted_donation.expiry_date,
            donation.expiry_date,
        )


class ImmediateInventoryReflectionTests(TestCase):
    def setUp(self):
        self.staff_group = Group.objects.create(
            name="Blood Bank Staff"
        )
        self.user = User.objects.create_user(
            username="inventory_staff",
            password="testpass123",
        )
        self.user.groups.add(self.staff_group)
        self.client.force_login(self.user)

        self.donor = Donor.objects.create(
            full_name="Inventory Test Donor",
            date_of_birth="2000-01-01",
            blood_group=Donor.BloodGroup.O_POSITIVE,
            phone_number="9876501234",
            address="Test Address",
        )

    def test_accepted_donation_immediately_updates_inventory(self):
        today = timezone.localdate()

        response = self.client.post(
            reverse("donations:record"),
            {
                "donor_id": self.donor.donor_id,
                "donation_date": today.isoformat(),
                "quantity_units": 3,
                "expiry_date": (
                    today + timedelta(days=30)
                ).isoformat(),
                "donation_status": Donation.DonationStatus.ACCEPTED,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(get_available_units("O+"), 3)

        dashboard_response = self.client.get(
            reverse("inventory:dashboard")
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(
            dashboard_response.context["inventory"]["O+"],
            3,
        )

    def test_inventory_dashboard_refresh_shows_latest_quantity(self):
        today = timezone.localdate()

        response = self.client.post(
            reverse("donations:record"),
            {
                "donor_id": self.donor.donor_id,
                "donation_date": today.isoformat(),
                "quantity_units": 3,
                "expiry_date": (
                    today + timedelta(days=30)
                ).isoformat(),
                "donation_status": Donation.DonationStatus.ACCEPTED,
            },
        )

        self.assertEqual(response.status_code, 302)

        first_dashboard_response = self.client.get(
            reverse("inventory:dashboard")
        )

        self.assertEqual(
            first_dashboard_response.status_code,
            200,
        )
        self.assertEqual(
            first_dashboard_response.context["inventory"]["O+"],
            3,
        )

        response = self.client.post(
            reverse("donations:record"),
            {
                "donor_id": self.donor.donor_id,
                "donation_date": today.isoformat(),
                "quantity_units": 2,
                "expiry_date": (
                    today + timedelta(days=30)
                ).isoformat(),
                "donation_status": Donation.DonationStatus.ACCEPTED,
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(get_available_units("O+"), 5)

        refreshed_dashboard_response = self.client.get(
            reverse("inventory:dashboard")
        )

        self.assertEqual(
            refreshed_dashboard_response.status_code,
            200,
        )
        self.assertEqual(
            refreshed_dashboard_response.context["inventory"]["O+"],
            5,
        )
