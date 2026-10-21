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