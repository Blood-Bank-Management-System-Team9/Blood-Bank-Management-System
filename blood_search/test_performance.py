"""
E6-S1 (search part): Blood availability search response time.

Requirement: NFR-01 - blood availability search shall respond within
3 seconds under normal operating conditions (10,000 donor records).
Test Plan: TC-PERF-01 (single-user response time check).

The multi-user part of TC-PERF-01 (20 concurrent users) is run
separately as a load test during system testing.
"""

import time
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from donations.models import Donation
from donors.models import Donor


DONOR_COUNT = 10_000
DONATIONS_PER_DONOR = 3
MAX_RESPONSE_SECONDS = 3.0
BLOOD_GROUPS = [value for value, _label in Donor.BloodGroup.choices]


class BloodAvailabilitySearchPerformanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.localdate()

        donors = [
            Donor(
                full_name=f"Perf Donor {i}",
                date_of_birth="1995-01-01",
                blood_group=BLOOD_GROUPS[i % len(BLOOD_GROUPS)],
                phone_number=f"9{i:09d}",
                address="Bengaluru",
            )
            for i in range(DONOR_COUNT)
        ]
        Donor.objects.bulk_create(donors, batch_size=2000)

        statuses = ["Accepted", "Accepted", "Pending", "Rejected"]
        donations = []
        for i, donor in enumerate(Donor.objects.all()):
            for j in range(DONATIONS_PER_DONOR):
                donations.append(
                    Donation(
                        donor=donor,
                        blood_group=donor.blood_group,
                        donation_date=today,
                        quantity_units=1,
                        # Mix of valid and expired units.
                        expiry_date=today + timedelta(days=(i + j) % 40 - 5),
                        donation_status=statuses[(i + j) % len(statuses)],
                    )
                )
        Donation.objects.bulk_create(donations, batch_size=5000)

        group = Group.objects.create(name="Hospital Staff")
        user = User.objects.create_user(
            username="perfhospital",
            password="testpass123",
        )
        user.groups.add(group)

    def setUp(self):
        self.url = reverse("blood_search:availability")
        self.client.login(username="perfhospital", password="testpass123")

    def test_availability_search_responds_within_3_seconds(self):
        """
        TC-PERF-01 / NFR-01:
        With 10,000 donors and 30,000 donations, every blood group
        search returns within 3 seconds.
        """
        self.assertEqual(Donor.objects.count(), DONOR_COUNT)
        self.assertEqual(
            Donation.objects.count(),
            DONOR_COUNT * DONATIONS_PER_DONOR,
        )

        timings = {}

        for blood_group in BLOOD_GROUPS:
            start = time.perf_counter()
            response = self.client.get(self.url, {"blood_group": blood_group})
            elapsed = time.perf_counter() - start

            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.context["result"])
            timings[blood_group] = elapsed

        slowest_group = max(timings, key=timings.get)
        slowest = timings[slowest_group]

        print(
            "\n[TC-PERF-01] Availability search response times (s): "
            + ", ".join(f"{g}={t:.3f}" for g, t in timings.items())
            + f" | slowest: {slowest_group} {slowest:.3f}s"
        )

        self.assertLess(
            slowest,
            MAX_RESPONSE_SECONDS,
            f"Search for {slowest_group} took {slowest:.3f}s "
            f"(limit {MAX_RESPONSE_SECONDS}s).",
        )
