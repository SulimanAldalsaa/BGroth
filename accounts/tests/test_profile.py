from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import User

PASSWORD = "S3cure!Pass99"
ME_URL = "/api/auth/me/"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ProfileUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="merchant@example.com",
            password=PASSWORD,
            first_name="Ahmad",
            last_name="Yousef",
        )
        self.client_a = APIClient()
        tokens = self.client_a.post(
            "/api/auth/login/",
            {"email": "merchant@example.com", "password": PASSWORD},
            format="json",
        ).json()["tokens"]
        self.client_a.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])

    def test_can_update_first_name(self):
        response = self.client_a.patch(ME_URL, {"first_name": "Khalid"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["first_name"], "Khalid")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Khalid")

    def test_can_update_last_name(self):
        response = self.client_a.patch(ME_URL, {"last_name": "Hassan"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["last_name"], "Hassan")

    def test_partial_update_leaves_other_field_untouched(self):
        response = self.client_a.patch(ME_URL, {"first_name": "Khalid"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["last_name"], "Yousef")

    def test_can_update_both_fields_together(self):
        response = self.client_a.patch(
            ME_URL, {"first_name": "Khalid", "last_name": "Hassan"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["first_name"], "Khalid")
        self.assertEqual(body["last_name"], "Hassan")
        self.assertEqual(body["full_name"], "Khalid Hassan")

    def test_blank_names_are_allowed(self):
        response = self.client_a.patch(ME_URL, {"first_name": "", "last_name": ""}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["first_name"], "")

    def test_unauthenticated_request_gets_401(self):
        response = APIClient().patch(ME_URL, {"first_name": "Khalid"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_email_cannot_be_changed(self):
        response = self.client_a.patch(ME_URL, {"email": "new@example.com"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "merchant@example.com")

    def test_protected_fields_cannot_be_changed(self):
        for field, value in (
            ("is_active", False),
            ("is_staff", True),
            ("is_email_verified", True),
            ("id", "11111111-1111-1111-1111-111111111111"),
            ("date_joined", "2000-01-01T00:00:00Z"),
            ("full_name", "Someone Else"),
        ):
            response = self.client_a.patch(ME_URL, {field: value}, format="json")
            self.assertEqual(response.status_code, 400, field)
            self.assertIn(field, response.json(), field)

    def test_rejected_edit_does_not_apply_other_fields(self):
        response = self.client_a.patch(
            ME_URL, {"first_name": "Khalid", "email": "new@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ahmad")

    def test_password_field_is_protected(self):
        response = self.client_a.patch(ME_URL, {"password": "NewPass123!"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_get_response_shape_is_unchanged(self):
        response = self.client_a.get(ME_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {
                "id", "email", "first_name", "last_name", "full_name",
                "is_active", "is_email_verified", "date_joined",
            },
        )

    def test_invalid_field_type_returns_400(self):
        response = self.client_a.patch(
            ME_URL, {"first_name": ["not", "a", "string"]}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("first_name", response.json())

    def test_first_name_too_long_returns_400(self):
        response = self.client_a.patch(ME_URL, {"first_name": "x" * 200}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("first_name", response.json())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ExistingAuthEndpointsRegressionTests(APITestCase):
    """Confirm Phase 4 did not disturb any other accounts/ endpoint."""

    def test_register_still_works(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "new-user@example.com",
                "first_name": "Sara",
                "last_name": "Ali",
                "password": PASSWORD,
                "password_confirm": PASSWORD,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIn("tokens", response.json())

    def test_login_still_works(self):
        User.objects.create_user(email="login@example.com", password=PASSWORD)
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access", response.json()["tokens"])

    def test_login_with_wrong_password_is_400(self):
        User.objects.create_user(email="login2@example.com", password=PASSWORD)
        response = self.client.post(
            "/api/auth/login/",
            {"email": "login2@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_get_me_still_requires_authentication(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, 401)

    def test_change_password_still_works(self):
        User.objects.create_user(email="pw@example.com", password=PASSWORD)
        client = APIClient()
        tokens = client.post(
            "/api/auth/login/", {"email": "pw@example.com", "password": PASSWORD}, format="json"
        ).json()["tokens"]
        client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        response = client.post(
            "/api/auth/change-password/",
            {
                "old_password": PASSWORD,
                "new_password": "NewS3cure!Pass1",
                "new_password_confirm": "NewS3cure!Pass1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_token_refresh_still_works(self):
        User.objects.create_user(email="refresh@example.com", password=PASSWORD)
        tokens = self.client.post(
            "/api/auth/login/",
            {"email": "refresh@example.com", "password": PASSWORD},
            format="json",
        ).json()["tokens"]
        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access", response.json())
