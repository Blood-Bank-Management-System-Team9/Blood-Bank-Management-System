import json
import re
from datetime import date, timedelta
from itertools import count
from pathlib import Path

from locust import HttpUser, between, task


CONFIG_PATH = Path(__file__).with_name("perf_config.json")

if not CONFIG_PATH.exists():
    raise RuntimeError(
        "performance/perf_config.json does not exist. "
        "Run: python manage.py seed_perf_data --requests 10000"
    )

CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

DONOR_ID = CONFIG["donor_id"]
STAFF_USERNAME = CONFIG["staff_username"]
HOSPITAL_USERNAME = CONFIG["hospital_username"]
PASSWORD = CONFIG["password"]
ISSUE_REQUEST_COUNT = CONFIG["issue_request_count"]

CSRF_PATTERN = re.compile(
    r'name="csrfmiddlewaretoken"\s+value="([^"]+)"'
)

issue_counter = count(1)


class BBMSPerformanceUser(HttpUser):
    abstract = True
    wait_time = between(0.5, 1.5)

    username = ""

    def on_start(self):
        self.login()

    def login(self):
        response = self.client.get(
            "/accounts/login/",
            name="SETUP login page",
        )

        match = CSRF_PATTERN.search(response.text)

        if match is None:
            raise RuntimeError(
                "Could not find CSRF token on /accounts/login/."
            )

        csrf_token = match.group(1)

        with self.client.post(
            "/accounts/login/",
            data={
                "username": self.username,
                "password": PASSWORD,
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={
                "X-CSRFToken": csrf_token,
            },
            allow_redirects=False,
            name="SETUP login",
            catch_response=True,
        ) as login_response:

            if login_response.status_code not in (302, 303):
                login_response.failure(
                    f"Login failed with status "
                    f"{login_response.status_code}"
                )
                raise RuntimeError(
                    f"Login failed for {self.username}"
                )

        self.csrf_token = self.client.cookies.get("csrftoken")

        if not self.csrf_token:
            raise RuntimeError(
                "Django did not return a CSRF cookie after login."
            )

    def csrf_headers(self):
        return {
            "X-CSRFToken": self.csrf_token,
        }


class DonationSubmissionUser(BBMSPerformanceUser):
    """
    Seven concurrent virtual users repeatedly record valid donations.
    """

    fixed_count = 7
    username = STAFF_USERNAME

    @task
    def submit_donation(self):
        today = date.today()

        payload = {
            "donor_id": DONOR_ID,
            "donation_date": today.isoformat(),
            "quantity_units": 1,
            "expiry_date": (
                today + timedelta(days=30)
            ).isoformat(),
            "donation_status": "Accepted",
        }

        with self.client.post(
            "/api/donations",
            data=payload,
            headers=self.csrf_headers(),
            allow_redirects=False,
            name="Donation submission",
            catch_response=True,
        ) as response:

            if response.status_code != 302:
                response.failure(
                    f"Expected 302, got {response.status_code}"
                )
            else:
                response.success()


class RequestSubmissionUser(BBMSPerformanceUser):
    """
    Seven concurrent virtual users repeatedly submit valid blood requests.
    """

    fixed_count = 7
    username = HOSPITAL_USERNAME

    @task
    def submit_request(self):
        payload = {
            "hospital_name": "PERF REQUEST LOAD",
            "patient_name": "Performance Patient",
            "blood_group": "A+",
            "units_required": 1,
            "required_by_date": "",
            "reason": "E6-S2 performance test",
        }

        with self.client.post(
            "/requests/new/",
            data=payload,
            headers=self.csrf_headers(),
            allow_redirects=False,
            name="Request submission",
            catch_response=True,
        ) as response:

            if response.status_code != 302:
                response.failure(
                    f"Expected 302, got {response.status_code}"
                )
            else:
                response.success()


class IssueSubmissionUser(BBMSPerformanceUser):
    """
    Six concurrent virtual users issue different pre-approved requests.
    """

    fixed_count = 6
    username = STAFF_USERNAME

    @task
    def submit_issue(self):
        request_number = next(issue_counter)

        if request_number > ISSUE_REQUEST_COUNT:
            raise RuntimeError(
                "Performance issue request pool exhausted. "
                "Seed more requests before running the test."
            )

        request_id = f"P{request_number:09d}"

        with self.client.post(
            "/api/issues",
            data={
                "request_id": request_id,
            },
            headers=self.csrf_headers(),
            name="Issue submission",
            catch_response=True,
        ) as response:

            if response.status_code != 201:
                response.failure(
                    f"Expected 201, got {response.status_code}: "
                    f"{response.text}"
                )
            else:
                response.success()