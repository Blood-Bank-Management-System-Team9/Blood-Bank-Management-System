from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.decorators import role_required
from accounts.models import UserProfile


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="staff1", password="pass12345")

    def test_login_success(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "staff1", "password": "pass12345"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_login_failure(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "staff1", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_logout_clears_session(self):
        self.client.login(username="staff1", password="pass12345")
        self.client.post(reverse("accounts:logout"))
        self.assertFalse("_auth_user_id" in self.client.session)


class RoleRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.staff_user = User.objects.create_user(username="staff2", password="pass12345")
        self.staff_user.profile.role = UserProfile.Role.STAFF
        self.staff_user.profile.save()

        self.hospital_user = User.objects.create_user(username="hosp1", password="pass12345")
        self.hospital_user.profile.role = UserProfile.Role.HOSPITAL
        self.hospital_user.profile.save()

    def test_profile_auto_created(self):
        self.assertTrue(UserProfile.objects.filter(user=self.staff_user).exists())

    def test_allowed_role_passes(self):
        @role_required(UserProfile.Role.STAFF)
        def view(request):
            return HttpResponse("ok")

        request = self.factory.get("/")
        request.user = self.staff_user
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_disallowed_role_is_forbidden(self):
        from django.core.exceptions import PermissionDenied

        @role_required(UserProfile.Role.STAFF)
        def view(request):
            return HttpResponse("ok")

        request = self.factory.get("/")
        request.user = self.hospital_user
        with self.assertRaises(PermissionDenied):
            view(request)