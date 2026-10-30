"""
E6-S8: Supported browser portability (NFR-08, TC-PORT-01).

Runs the core BBMS flow end-to-end in real browsers using Playwright:
login -> blood search -> submit request (+ validation) -> My Requests
-> staff review & approve -> All Requests filter -> hospital sees Approved
-> inventory dashboard. A screenshot of every page is saved per browser.

This test is SKIPPED by default (CI has no browsers). To run it:

    pip install playwright
    python -m playwright install firefox
    set BROWSER_TESTS=chrome,msedge,firefox          (Windows cmd)
    $env:BROWSER_TESTS="chrome,msedge,firefox"       (PowerShell)
    python manage.py test blood_requests.test_browser_portability -v 2

"chrome" and "msedge" use the browsers already installed on the computer.
Screenshots are written to browser_screenshots/<browser>/.
"""

import os
import unittest
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.utils import timezone

from donations.models import Donation
from donors.models import Donor

from .models import BloodRequest

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


BROWSERS = [
    b.strip().lower()
    for b in os.environ.get("BROWSER_TESTS", "").split(",")
    if b.strip()
]

PASSWORD = "Test@12345"


def launch(playwright, name):
    if name in ("chrome", "msedge"):
        return playwright.chromium.launch(channel=name)
    if name == "chromium":
        executable = os.environ.get("CHROMIUM_PATH") or None
        return playwright.chromium.launch(executable_path=executable)
    if name == "firefox":
        return playwright.firefox.launch()
    if name == "webkit":
        return playwright.webkit.launch()
    raise ValueError(f"Unknown browser '{name}'")


@unittest.skipUnless(
    BROWSERS and sync_playwright,
    "Set BROWSER_TESTS=chrome,msedge,firefox and install playwright to run.",
)
class BrowserPortabilityTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        # Playwright's sync API runs an event loop; allow Django DB access.
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        super().setUpClass()
        cls.playwright = sync_playwright().start()

    @classmethod
    def tearDownClass(cls):
        cls.playwright.stop()
        super().tearDownClass()

    def setUp(self):
        hospital_group = Group.objects.create(name="Hospital Staff")
        staff_group = Group.objects.create(name="Blood Bank Staff")

        User.objects.create_user("hospital1", password=PASSWORD).groups.add(
            hospital_group
        )
        User.objects.create_user("staff1", password=PASSWORD).groups.add(
            staff_group
        )

        today = timezone.localdate()
        donor = Donor.objects.create(
            full_name="Ravi Kumar",
            date_of_birth="1998-05-12",
            blood_group="O+",
            phone_number="9876543210",
            address="Bengaluru",
        )
        Donation.objects.create(
            donor=donor,
            donation_date=today,
            quantity_units=6,
            expiry_date=today + timedelta(days=30),
            donation_status="Accepted",
        )

    # ---------------- helpers ----------------

    def shot(self, page, browser_name, name):
        folder = Path(settings.BASE_DIR) / "browser_screenshots" / browser_name
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / f"{name}.png"), full_page=True)

    def login(self, page, username):
        page.goto(f"{self.live_server_url}/accounts/login/")
        page.fill("input[name=username]", username)
        page.fill("input[name=password]", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_load_state()
        self.assertNotIn("/accounts/login/", page.url, f"{username} login failed")

    def logout(self, page):
        page.click(".logout-form button")
        page.wait_for_load_state()

    def assert_layout_ok(self, page, where):
        """
        Basic layout check: nav bar visible and no horizontal overflow.
        """
        self.assertTrue(page.is_visible(".top-nav"), f"Nav bar missing on {where}")
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > "
            "document.documentElement.clientWidth + 1"
        )
        self.assertFalse(overflow, f"Horizontal overflow on {where}")

    # ---------------- the flow ----------------

    def run_flow(self, browser_name):
        browser = launch(self.playwright, browser_name)
        page = browser.new_page(viewport={"width": 1366, "height": 800})
        page.on("dialog", lambda dialog: dialog.accept())
        base = self.live_server_url

        try:
            # 1. Hospital logs in
            self.login(page, "hospital1")

            # 2. Blood search
            page.goto(f"{base}/blood-search/")
            page.select_option("#blood_group", "O+")
            page.click(".search-button")
            page.wait_for_load_state()
            self.assertIn("Available", page.inner_text(".result"))
            self.assertIn("6", page.inner_text(".result"))
            self.assert_layout_ok(page, "Blood Search")
            self.shot(page, browser_name, "01_blood_search")

            # 3. Validation: units missing
            page.goto(f"{base}/requests/new/?blood_group=O%2B")
            page.fill("#id_hospital_name", "City Hospital")
            page.fill("#id_patient_name", "Anita Rao")
            page.fill("#id_reason", "Surgery")
            page.click(".submit-button")
            page.wait_for_load_state()
            self.assertIn("This field is required.", page.content())
            self.assertEqual(BloodRequest.objects.count(), 0)
            self.assert_layout_ok(page, "Request Blood (errors)")
            self.shot(page, browser_name, "02_request_validation")

            # 4. Valid request -> My Requests shows Pending
            page.fill("#id_units_required", "2")
            page.click(".submit-button")
            page.wait_for_load_state()
            self.assertIn("/requests/mine/", page.url)
            blood_request = BloodRequest.objects.get()
            self.assertIn(blood_request.request_id, page.content())
            self.assertIn("Pending", page.inner_text("table"))
            self.assert_layout_ok(page, "My Requests")
            self.shot(page, browser_name, "03_my_requests_pending")

            # 5. Staff logs in, reviews and approves
            self.logout(page)
            self.login(page, "staff1")
            page.goto(f"{base}/requests/pending/")
            self.assertIn(blood_request.request_id, page.content())
            self.shot(page, browser_name, "04_pending_requests")
            page.click("a.view-link")
            page.wait_for_load_state()
            page.click("button.btn.approve")
            page.wait_for_load_state()
            blood_request.refresh_from_db()
            self.assertEqual(blood_request.status, "Approved")

            # 6. All Requests, Approved filter
            page.goto(f"{base}/requests/all/?status=Approved")
            self.assertIn(blood_request.request_id, page.content())
            self.assert_layout_ok(page, "All Requests")
            self.shot(page, browser_name, "05_all_requests_approved")

            # 7. Inventory dashboard
            page.goto(f"{base}/inventory/")
            self.assert_layout_ok(page, "Inventory")
            self.shot(page, browser_name, "06_inventory")

            # 8. Hospital sees Approved
            self.logout(page)
            self.login(page, "hospital1")
            page.goto(f"{base}/requests/mine/")
            self.assertIn("Approved", page.inner_text("table"))
            self.shot(page, browser_name, "07_my_requests_approved")

        finally:
            browser.close()

    def test_core_flow_in_each_browser(self):
        """
        TC-PORT-01 / NFR-08: the core flow works in every listed browser.
        """
        for browser_name in BROWSERS:
            with self.subTest(browser=browser_name):
                BloodRequest.objects.all().delete()
                self.run_flow(browser_name)
                print(f"\n[TC-PORT-01] {browser_name}: core flow PASSED")
