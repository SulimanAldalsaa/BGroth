from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import User

from .base import API, PASSWORD, BusinessAPITestCase


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthFlowTests(APITestCase):
    def test_register_login_me_refresh_logout(self):
        body = {
            "email": "new@example.com",
            "first_name": "New",
            "password": PASSWORD,
            "password_confirm": PASSWORD,
        }
        response = self.client.post("/api/auth/register/", body, format="json")
        self.assertEqual(response.status_code, 201)
        tokens = response.json()["tokens"]

        auth = APIClient()
        auth.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        self.assertEqual(auth.get("/api/auth/me/").json()["email"], "new@example.com")

        refreshed = self.client.post(
            "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("refresh", refreshed.json())

        reuse = self.client.post(
            "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(reuse.status_code, 401)

        auth.credentials(HTTP_AUTHORIZATION="Bearer " + refreshed.json()["access"])
        logout = auth.post(
            "/api/auth/logout/", {"refresh": refreshed.json()["refresh"]}, format="json"
        )
        self.assertEqual(logout.status_code, 200)

    def test_login_with_wrong_password_is_400(self):
        User.objects.create_user(email="x@example.com", password=PASSWORD)
        response = self.client.post(
            "/api/auth/login/", {"email": "x@example.com", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_business_endpoints_require_authentication(self):
        self.assertEqual(self.client.get(API + "products/").status_code, 401)


class BusinessTests(BusinessAPITestCase):
    def test_get_and_patch_business(self):
        self.assertEqual(self.client_a.get(API).json()["name"], "Shop A")
        response = self.client_a.patch(API, {"phone": "0790000000"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["phone"], "0790000000")

    def test_only_one_business_per_user(self):
        response = self.client_a.post(API, {"name": "Second"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_business_required_before_other_endpoints(self):
        client, _ = self.make_user("nobiz@example.com")
        self.assertEqual(client.get(API).status_code, 404)
        self.assertEqual(client.get(API + "products/").status_code, 404)
        self.assertEqual(client.get(API + "dashboard/").status_code, 404)

    def test_expenses_crud_and_category_filter(self):
        body = {"amount": "20", "category": "rent", "expense_date": "2026-09-01"}
        created = self.client_a.post(API + "expenses/", body, format="json")
        self.assertEqual(created.status_code, 201)
        self.client_a.post(API + "expenses/", {**body, "category": "tax"}, format="json")
        rent = self.client_a.get(API + "expenses/?category=rent").json()
        self.assertEqual(len(rent), 1)
        missing = self.client_a.post(API + "expenses/", {"amount": "1", "category": "x"}, format="json")
        self.assertEqual(missing.status_code, 400)
        expense_id = created.json()["id"]
        self.assertEqual(self.client_a.delete(API + f"expenses/{expense_id}/").status_code, 204)

    def test_categories_unique_per_business(self):
        self.assertEqual(self.client_a.post(API + "categories/", {"name": "Drinks"}, format="json").status_code, 201)
        self.assertEqual(self.client_a.post(API + "categories/", {"name": "Drinks"}, format="json").status_code, 400)
        self.assertEqual(self.client_b.post(API + "categories/", {"name": "Drinks"}, format="json").status_code, 201)


class IsolationTests(BusinessAPITestCase):
    """User B must never see or change user A's data (SRS BR-1 / NFR-4 / AC-7)."""

    def setUp(self):
        super().setUp()
        self.product = self.make_product()
        self.sale = self.make_sale(self.product["id"], quantity=1)
        self.customer = self.client_a.post(API + "customers/", {"name": "C-A"}, format="json").json()
        self.expense = self.client_a.post(
            API + "expenses/",
            {"amount": "1", "category": "x", "expense_date": "2026-09-01"},
            format="json",
        ).json()

    def test_lists_are_empty_for_other_user(self):
        for path in ("products/", "customers/", "sales/", "expenses/", "categories/"):
            self.assertEqual(self.client_b.get(API + path).json(), [], path)

    def test_detail_read_update_delete_are_404(self):
        targets = {
            "products": self.product["id"],
            "sales": self.sale["id"],
            "customers": self.customer["id"],
            "expenses": self.expense["id"],
        }
        for name, pk in targets.items():
            url = API + f"{name}/{pk}/"
            self.assertEqual(self.client_b.get(url).status_code, 404, name)
            self.assertEqual(self.client_b.patch(url, {}, format="json").status_code, 404, name)
            self.assertEqual(self.client_b.delete(url).status_code, 404, name)

    def test_cannot_pay_adjust_or_sell_foreign_objects(self):
        pay = self.client_b.post(
            API + f"sales/{self.sale['id']}/payments/",
            {"amount": "0.5", "payment_method": "CASH"},
            format="json",
        )
        self.assertEqual(pay.status_code, 400)
        adjust = self.client_b.post(
            API + f"products/{self.product['id']}/adjust-stock/",
            {"quantity": 1, "movement_type": "IN"},
            format="json",
        )
        self.assertEqual(adjust.status_code, 404)
        sell = self.client_b.post(
            API + "sales/",
            {"items": [{"product": self.product["id"], "quantity": 1}]},
            format="json",
        )
        self.assertEqual(sell.status_code, 400)
        history = self.client_b.get(API + f"customers/{self.customer['id']}/history/")
        self.assertEqual(history.status_code, 404)

    def test_cannot_use_foreign_category_on_product(self):
        category = self.client_a.post(API + "categories/", {"name": "Private"}, format="json").json()
        response = self.client_b.post(
            API + "products/",
            {"name": "X", "selling_price": "1", "category": category["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
