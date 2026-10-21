from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from donors.models import Donor

from .models import Donation


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

        self.assertEqual(
            donation.donor,
            donor,
        )

        self.assertTrue(
            donor.donation_set.filter(
                donation_id=donation.donation_id
            ).exists()
        )

        linked_donation = donor.donation_set.get(
            donation_id=donation.donation_id
        )

        self.assertEqual(
            linked_donation.blood_group,
            donor.blood_group,
        )

        self.assertEqual(
            linked_donation.quantity_units,
            1,
        )

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

        self.assertEqual(
            accepted_donation.quantity_units,
            1,
        )

        self.assertEqual(
            accepted_donation.donation_date,
            donation.donation_date,
        )

        self.assertEqual(
            accepted_donation.expiry_date,
            donation.expiry_date,
        )