from django.test import TestCase

# Create your tests here.
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .forms import DonorRegistrationForm
from .models import Donor


class DonorRegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("donors:register")

        self.blood_bank_staff_group = Group.objects.create(
            name="Blood Bank Staff"
        )

        self.staff_user = User.objects.create_user(
            username="bloodstaff",
            password="testpass123",
        )

        self.staff_user.groups.add(
            self.blood_bank_staff_group
        )

        self.valid_data = {
            "full_name": "Ravi Kumar",
            "date_of_birth": "1998-05-12",
            "blood_group": "O+",
            "phone_number": "9876543210",
            "email": "",
            "address": "Bengaluru",
            "status": "Active",
        }

    def test_valid_donor_registration(self):
        """
        TC-DON-01:
        Valid donor information should create a donor record,
        store the blood group, generate a donor ID, and show
        a success message.
        """
        self.client.login(
            username="bloodstaff",
            password="testpass123",
        )

        response = self.client.post(
            self.url,
            data=self.valid_data,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(Donor.objects.count(), 1)

        donor = Donor.objects.get(
            phone_number="9876543210"
        )

        self.assertEqual(
            donor.full_name,
            "Ravi Kumar",
        )

        self.assertEqual(
            donor.blood_group,
            "O+",
        )

        self.assertEqual(
            len(donor.donor_id),
            10,
        )

        self.assertTrue(
            donor.donor_id.isalnum()
        )

        self.assertContains(
            response,
            "registered successfully",
        )

        self.assertContains(
            response,
            donor.donor_id,
        )

    def test_invalid_donor_registration(self):
        """
        TC-DON-02:
        Missing blood group and invalid phone number must
        produce validation errors and must not save a donor.
        """
        self.client.login(
            username="bloodstaff",
            password="testpass123",
        )

        invalid_data = self.valid_data.copy()

        invalid_data["blood_group"] = ""
        invalid_data["phone_number"] = "98AB"

        response = self.client.post(
            self.url,
            data=invalid_data,
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            Donor.objects.count(),
            0,
        )

        self.assertFormError(
            response.context["form"],
            "blood_group",
            "This field is required.",
        )

        self.assertFormError(
            response.context["form"],
            "phone_number",
            (
                "Enter a valid phone number using digits only "
                "(maximum 15 digits)."
            ),
        )

    def test_mandatory_fields_are_required(self):
        """
        FR-1.2:
        Mandatory donor information must be supplied.
        """
        form = DonorRegistrationForm(
            data={}
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            "full_name",
            form.errors,
        )

        self.assertIn(
            "date_of_birth",
            form.errors,
        )

        self.assertIn(
            "blood_group",
            form.errors,
        )

        self.assertIn(
            "phone_number",
            form.errors,
        )

        self.assertIn(
            "status",
            form.errors,
        )

    def test_unauthenticated_user_cannot_register_donor(self):
        """
        FR-1.1:
        Donor registration is a protected operation.
        """
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            Donor.objects.count(),
            0,
        )

    def test_non_blood_bank_staff_cannot_register_donor(self):
        """
        FR-1.1:
        An authenticated user without the Blood Bank Staff
        role must not be allowed to register donors.
        """
        User.objects.create_user(
            username="otheruser",
            password="testpass123",
        )

        self.client.login(
            username="otheruser",
            password="testpass123",
        )

        response = self.client.post(
            self.url,
            data=self.valid_data,
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.assertEqual(
            Donor.objects.count(),
            0,
        )

class DonorSearchUpdateTests(TestCase):
    def setUp(self):
        self.blood_bank_staff_group = Group.objects.create(
            name="Blood Bank Staff"
        )

        self.staff_user = User.objects.create_user(
            username="bloodstaff",
            password="testpass123",
        )

        self.staff_user.groups.add(
            self.blood_bank_staff_group
        )

        self.donor = Donor.objects.create(
            full_name="Ravi Kumar",
            date_of_birth="1998-05-12",
            blood_group="O+",
            phone_number="9876543210",
            email="",
            address="Bengaluru",
            status="Active",
        )

        self.other_donor = Donor.objects.create(
            full_name="Anita Sharma",
            date_of_birth="1995-08-20",
            blood_group="A+",
            phone_number="9123456789",
            email="",
            address="Bengaluru",
            status="Active",
        )

        self.search_url = reverse(
            "donors:search"
        )

        self.update_url = reverse(
            "donors:update",
            kwargs={
                "donor_id": self.donor.donor_id,
            },
        )

    def test_staff_can_search_donor_by_phone(self):
        """
        TC-DON-03 / FR-1.4:
        Searching by phone number should return exactly
        the matching donor.
        """
        self.client.login(
            username="bloodstaff",
            password="testpass123",
        )

        response = self.client.get(
            self.search_url,
            {
                "phone_number": "9876543210",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        donors = response.context["donors"]

        self.assertEqual(
            donors.count(),
            1,
        )

        self.assertEqual(
            donors.first(),
            self.donor,
        )

        self.assertContains(
            response,
            "Ravi Kumar",
        )

        self.assertContains(
            response,
            "9876543210",
        )

    def test_staff_can_update_donor_address(self):
        """
        TC-DON-03 / FR-1.5:
        Authorized staff should be able to change the
        donor address to Mysuru and receive a success message.
        """
        self.client.login(
            username="bloodstaff",
            password="testpass123",
        )

        updated_data = {
            "full_name": "Ravi Kumar",
            "date_of_birth": "1998-05-12",
            "blood_group": "O+",
            "phone_number": "9876543210",
            "email": "",
            "address": "Mysuru",
            "status": "Active",
        }

        response = self.client.post(
            self.update_url,
            data=updated_data,
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.donor.refresh_from_db()

        self.assertEqual(
            self.donor.address,
            "Mysuru",
        )

        self.assertEqual(
            Donor.objects.count(),
            2,
        )

        self.assertContains(
            response,
            "updated successfully",
        )

        self.assertContains(
            response,
            "Mysuru",
        )

    def test_non_blood_bank_staff_cannot_search_donors(self):
        """
        FR-1.4:
        An authenticated user without the Blood Bank Staff
        role must not be allowed to search donor records.
        """
        User.objects.create_user(
            username="otheruser",
            password="testpass123",
        )

        self.client.login(
            username="otheruser",
            password="testpass123",
        )

        response = self.client.get(
            self.search_url,
            {
                "phone_number": "9876543210",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

    def test_non_blood_bank_staff_cannot_update_donor(self):
        """
        FR-1.5:
        An authenticated user without the Blood Bank Staff
        role must not be allowed to update donor records.
        """
        User.objects.create_user(
            username="otheruser",
            password="testpass123",
        )

        self.client.login(
            username="otheruser",
            password="testpass123",
        )

        response = self.client.post(
            self.update_url,
            data={
                "full_name": "Ravi Kumar",
                "date_of_birth": "1998-05-12",
                "blood_group": "O+",
                "phone_number": "9876543210",
                "email": "",
                "address": "Mysuru",
                "status": "Active",
            },
        )

        self.assertEqual(
            response.status_code,
            403,
        )

        self.donor.refresh_from_db()

        self.assertEqual(
            self.donor.address,
            "Bengaluru",
        )