
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from donors.models import Donor
from donations.models import Donation
from inventory.services import (
    get_available_units,
    get_inventory_by_blood_group,
    get_near_expiry_donations,
    get_expired_donations,
    get_low_stock_groups,
)


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.donor = Donor.objects.create(
            full_name="Test Donor",
            date_of_birth="2000-01-01",
            blood_group=Donor.BloodGroup.O_POSITIVE,
            phone_number="9876543210",
            address="Test Address",
        )

    def create_donation(self, quantity, status, expiry_date):
        return Donation.objects.create(
            donor=self.donor,
            donation_date=timezone.localdate(),
            quantity_units=quantity,
            expiry_date=expiry_date,
            donation_status=status,
        )

    def test_available_units_exclude_expired_donations(self):
        today = timezone.localdate()

        self.create_donation(
            4, Donation.DonationStatus.ACCEPTED, today
        )
        self.create_donation(
            3, Donation.DonationStatus.ACCEPTED, today - timedelta(days=1)
        )
        self.create_donation(
            2, Donation.DonationStatus.PENDING, today + timedelta(days=3)
        )

        self.assertEqual(get_available_units("O+"), 4)

    def test_inventory_contains_all_blood_groups(self):
        inventory = get_inventory_by_blood_group()

        self.assertEqual(set(inventory.keys()), set(
            value for value, _label in Donor.BloodGroup.choices
        ))

    def test_near_expiry_donations_within_seven_days(self):
        today = timezone.localdate()

        expiring = self.create_donation(
            2,
            Donation.DonationStatus.ACCEPTED,
            today + timedelta(days=7),
        )
        self.create_donation(
            2,
            Donation.DonationStatus.ACCEPTED,
            today + timedelta(days=8),
        )

        results = get_near_expiry_donations()
        self.assertIn(expiring, results)
        self.assertEqual(results.count(), 1)

    def test_expired_donations_are_reported(self):
        today = timezone.localdate()

        expired = self.create_donation(
            1,
            Donation.DonationStatus.ACCEPTED,
            today - timedelta(days=1),
        )

        results = get_expired_donations()
        self.assertIn(expired, results)

    def test_low_stock_groups_use_fewer_than_five_units(self):
        today = timezone.localdate()

        self.create_donation(
            4,
            Donation.DonationStatus.ACCEPTED,
            today + timedelta(days=10),
        )

        low_stock = get_low_stock_groups()

        self.assertEqual(low_stock["O+"], 4)
        self.assertIn("A+", low_stock)
        self.assertEqual(low_stock["A+"], 0)