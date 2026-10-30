
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from donors.models import Donor
from donations.models import Donation
from issues.services import validate_stock_for_issue


class StockValidationTests(TestCase):
    def setUp(self):
        self.donor = Donor.objects.create(
            full_name="Test Donor",
            date_of_birth="2000-01-01",
            blood_group=Donor.BloodGroup.O_POSITIVE,
            phone_number="9876501234",
            address="Test Address",
        )

        Donation.objects.create(
            donor=self.donor,
            donation_date=timezone.localdate(),
            quantity_units=5,
            expiry_date=timezone.localdate() + timedelta(days=30),
            donation_status=Donation.DonationStatus.ACCEPTED,
        )

    def test_allows_issue_when_stock_is_sufficient(self):
        available = validate_stock_for_issue("O+", 3)
        self.assertEqual(available, 5)

    def test_allows_issue_when_requested_equals_available(self):
        available = validate_stock_for_issue("O+", 5)
        self.assertEqual(available, 5)

    def test_rejects_issue_when_stock_is_insufficient(self):
        with self.assertRaises(ValidationError):
            validate_stock_for_issue("O+", 7)

    def test_rejects_issue_when_no_stock_is_available(self):
        with self.assertRaises(ValidationError):
            validate_stock_for_issue("A+", 1)

    def test_rejects_zero_requested_units(self):
        with self.assertRaises(ValidationError):
            validate_stock_for_issue("O+", 0)

    def test_rejects_negative_requested_units(self):
        with self.assertRaises(ValidationError):
            validate_stock_for_issue("O+", -2)

