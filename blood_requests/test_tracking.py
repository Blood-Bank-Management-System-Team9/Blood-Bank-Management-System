"""
E4-S3: Review and track blood request status (FR-6.5, FR-6.6).
"""

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import BloodRequest
from .services import approve_request, reject_request


class TrackRequestStatusTests(TestCase):
    def setUp(self):
        self.mine_url = reverse("blood_requests:mine")
        self.all_url = reverse("blood_requests:all")
        self.submit_url = reverse("blood_requests:submit")

        hospital_group = Group.objects.create(name="Hospital Staff")
        staff_group = Group.objects.create(name="Blood Bank Staff")

        self.hospital_a = User.objects.create_user(
            username="hospital_a", password="testpass123"
        )
        self.hospital_a.groups.add(hospital_group)

        self.hospital_b = User.objects.create_user(
            username="hospital_b", password="testpass123"
        )
        self.hospital_b.groups.add(hospital_group)

        self.staff = User.objects.create_user(
            username="bloodstaff", password="testpass123"
        )
        self.staff.groups.add(staff_group)

        self.request_a1 = self.make_request(self.hospital_a, "A+", "City Hospital")
        self.request_a2 = self.make_request(self.hospital_a, "O-", "City Hospital")
        self.request_b1 = self.make_request(self.hospital_b, "B+", "Metro Clinic")

    def make_request(self, user, blood_group, hospital_name):
        return BloodRequest.objects.create(
            requested_by=user,
            hospital_name=hospital_name,
            patient_name="Test Patient",
            blood_group=blood_group,
            units_required=2,
            reason="Surgery",
        )

    def login(self, username):
        self.client.login(username=username, password="testpass123")

    # ---------------- FR-6.6: requesting user tracks status ----------------

    def test_hospital_sees_own_requests_with_status(self):
        """
        TC-REQ-01 (track part) / FR-6.6:
        Hospital Staff see their own requests with status Pending.
        """
        self.login("hospital_a")

        response = self.client.get(self.mine_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.request_a1.request_id)
        self.assertContains(response, self.request_a2.request_id)
        self.assertContains(response, "Pending")

    def test_hospital_does_not_see_other_hospitals_requests(self):
        """
        SEC-03 / SO-01: users only see their own requests.
        """
        self.login("hospital_a")

        response = self.client.get(self.mine_url)

        self.assertNotContains(response, self.request_b1.request_id)
        self.assertEqual(len(response.context["blood_requests"]), 2)

    def test_status_reflects_approval_and_rejection(self):
        """
        TC-ISS-01 (status part) / FR-6.6:
        After staff approve or reject, the hospital sees the new status
        and the staff note.
        """
        approve_request(self.request_a1, self.staff, "Collect from counter 2")
        reject_request(self.request_a2, self.staff, "Insufficient stock")

        self.login("hospital_a")

        response = self.client.get(self.mine_url)

        statuses = {
            r.request_id: r.status for r in response.context["blood_requests"]
        }

        self.assertEqual(statuses[self.request_a1.request_id], "Approved")
        self.assertEqual(statuses[self.request_a2.request_id], "Rejected")
        self.assertContains(response, "Collect from counter 2")
        self.assertContains(response, "Insufficient stock")

    def test_my_requests_status_filter(self):
        """
        Filtering My Requests by status shows only matching requests.
        """
        approve_request(self.request_a1, self.staff)

        self.login("hospital_a")

        response = self.client.get(self.mine_url, {"status": "Approved"})

        ids = [r.request_id for r in response.context["blood_requests"]]

        self.assertEqual(ids, [self.request_a1.request_id])

    def test_unknown_status_filter_is_ignored(self):
        self.login("hospital_a")

        response = self.client.get(self.mine_url, {"status": "Hacked"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["blood_requests"]), 2)

    def test_submit_redirects_to_my_requests_showing_pending(self):
        """
        TC-REQ-01 steps 3-4: after submitting, the user lands on
        My Requests and sees the new request as Pending.
        """
        self.login("hospital_a")

        response = self.client.post(
            self.submit_url,
            {
                "hospital_name": "City Hospital",
                "patient_name": "New Patient",
                "blood_group": "AB+",
                "units_required": 1,
                "required_by_date": "",
                "reason": "Emergency",
            },
            follow=True,
        )

        new_request = BloodRequest.objects.get(patient_name="New Patient")

        self.assertRedirects(response, self.mine_url)
        self.assertContains(response, new_request.request_id)
        self.assertEqual(new_request.status, "Pending")

    def test_script_in_review_note_is_escaped(self):
        """
        TC-SEC-06 (track part) / SEC-09: text is shown, never executed.
        """
        reject_request(self.request_a1, self.staff, "<script>alert(1)</script>")

        self.login("hospital_a")

        response = self.client.get(self.mine_url)

        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_staff_cannot_open_my_requests(self):
        self.login("bloodstaff")

        response = self.client.get(self.mine_url)

        self.assertEqual(response.status_code, 403)

    # ---------------- FR-6.5: staff review all submitted requests ----------------

    def test_staff_sees_all_requests_from_all_hospitals(self):
        """
        TC-REQ-01 step 5 / FR-6.5:
        Blood Bank Staff see every submitted request.
        """
        self.login("bloodstaff")

        response = self.client.get(self.all_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["blood_requests"]), 3)
        self.assertContains(response, "City Hospital")
        self.assertContains(response, "Metro Clinic")

    def test_staff_all_requests_status_filter(self):
        reject_request(self.request_b1, self.staff)

        self.login("bloodstaff")

        response = self.client.get(self.all_url, {"status": "Rejected"})

        ids = [r.request_id for r in response.context["blood_requests"]]

        self.assertEqual(ids, [self.request_b1.request_id])

    def test_hospital_cannot_open_all_requests(self):
        """
        TC-SEC-02 / SEC-02: Hospital Staff cannot see other hospitals'
        requests through the staff list.
        """
        self.login("hospital_a")

        response = self.client.get(self.all_url)

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_users_are_redirected(self):
        """
        TC-SEC-01 / SEC-01.
        """
        self.assertEqual(self.client.get(self.mine_url).status_code, 302)
        self.assertEqual(self.client.get(self.all_url).status_code, 302)
