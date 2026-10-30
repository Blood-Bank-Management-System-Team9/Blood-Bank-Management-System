import json
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from blood_requests.models import BloodRequest
from donations.models import Donation
from donors.models import Donor
from issues.models import BloodIssue


STAFF_USERNAME = "perf_staff"
HOSPITAL_USERNAME = "perf_hospital"
PASSWORD = "PerfTest123!"

PERF_REQUEST_PREFIX = "PERF "
ISSUE_REQUEST_PREFIX = "P"


class Command(BaseCommand):
    help = "Seed data required for E6-S2 / TC-PERF-02 performance testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--requests",
            type=int,
            default=10000,
            help="Number of approved requests to prepare for issue testing.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        request_count = options["requests"]

        if request_count < 100:
            self.stderr.write(
                self.style.ERROR(
                    "--requests must be at least 100."
                )
            )
            return

        self.stdout.write("Removing previous E6-S2 performance data...")

        # Remove issue records first because BloodRequest is protected
        # by BloodIssue.
        BloodIssue.objects.filter(
            blood_request__hospital_name__startswith=PERF_REQUEST_PREFIX
        ).delete()

        BloodRequest.objects.filter(
            hospital_name__startswith=PERF_REQUEST_PREFIX
        ).delete()

        Donation.objects.filter(
            donor__full_name__startswith=PERF_REQUEST_PREFIX
        ).delete()

        Donor.objects.filter(
            full_name__startswith=PERF_REQUEST_PREFIX
        ).delete()

        User.objects.filter(
            username__in=[STAFF_USERNAME, HOSPITAL_USERNAME]
        ).delete()

        staff_group, _ = Group.objects.get_or_create(
            name="Blood Bank Staff"
        )

        hospital_group, _ = Group.objects.get_or_create(
            name="Hospital Staff"
        )

        staff_user = User.objects.create_user(
            username=STAFF_USERNAME,
            password=PASSWORD,
        )
        staff_user.groups.add(staff_group)

        hospital_user = User.objects.create_user(
            username=HOSPITAL_USERNAME,
            password=PASSWORD,
        )
        hospital_user.groups.add(hospital_group)

        today = timezone.localdate()

        # B+ is used only by the donation-submission load.
        donation_donor = Donor.objects.create(
            full_name="PERF DONATION DONOR",
            date_of_birth=date(1995, 1, 1),
            blood_group="B+",
            phone_number="7999999991",
            address="Performance Test",
        )

        # AB- is isolated for the issue-submission load.
        issue_donor = Donor.objects.create(
            full_name="PERF ISSUE DONOR",
            date_of_birth=date(1995, 1, 2),
            blood_group="AB-",
            phone_number="7999999992",
            address="Performance Test",
        )

        # One large accepted batch keeps issue testing independent from
        # the B+ donations created during the load test.
        Donation.objects.create(
            donor=issue_donor,
            donation_date=today,
            quantity_units=request_count + 1000,
            expiry_date=today + timedelta(days=30),
            donation_status=Donation.DonationStatus.ACCEPTED,
        )

        self.stdout.write(
            f"Creating {request_count} approved issue requests..."
        )

        requests_to_create = []

        for number in range(1, request_count + 1):
            request_id = f"{ISSUE_REQUEST_PREFIX}{number:09d}"

            requests_to_create.append(
                BloodRequest(
                    request_id=request_id,
                    requested_by=hospital_user,
                    hospital_name="PERF ISSUE HOSPITAL",
                    patient_name=f"Performance Patient {number}",
                    blood_group="AB-",
                    units_required=1,
                    reason="E6-S2 performance test",
                    status=BloodRequest.Status.APPROVED,
                )
            )

        BloodRequest.objects.bulk_create(
            requests_to_create,
            batch_size=1000,
        )

        performance_dir = Path(settings.BASE_DIR) / "performance"
        performance_dir.mkdir(exist_ok=True)

        config_path = performance_dir / "perf_config.json"

        config_path.write_text(
            json.dumps(
                {
                    "donor_id": donation_donor.donor_id,
                    "issue_request_count": request_count,
                    "staff_username": STAFF_USERNAME,
                    "hospital_username": HOSPITAL_USERNAME,
                    "password": PASSWORD,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "E6-S2 performance data created successfully."
            )
        )

        self.stdout.write(
            f"Donation donor ID: {donation_donor.donor_id}"
        )

        self.stdout.write(
            f"Approved issue requests: {request_count}"
        )

        self.stdout.write(
            f"Config written to: {config_path}"
        )