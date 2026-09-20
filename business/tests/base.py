from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import User

PASSWORD = "S3cure!Pass99"
API = "/api/business/"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BusinessAPITestCase(APITestCase):
    """Two merchants (A and B), each with their own business and client."""

    def setUp(self):
        self.client_a, self.user_a = self.make_user("a@example.com")
        self.client_b, self.user_b = self.make_user("b@example.com")
        self.business_a = self.client_a.post(API, {"name": "Shop A"}, format="json").json()
        self.client_b.post(API, {"name": "Shop B"}, format="json")

    def make_user(self, email):
        user = User.objects.create_user(email=email, password=PASSWORD)
        client = APIClient()
        tokens = client.post(
            "/api/auth/login/", {"email": email, "password": PASSWORD}, format="json"
        ).json()["tokens"]
        client.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        return client, user

    def make_product(self, client=None, **overrides):
        data = {"name": "Cola", "selling_price": "2.50", "initial_quantity": 10, "minimum_stock": 3}
        data.update(overrides)
        response = (client or self.client_a).post(API + "products/", data, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def make_sale(self, product_id, quantity=4, paid="0", customer=None):
        payload = {"paid_amount": paid, "items": [{"product": product_id, "quantity": quantity}]}
        if customer:
            payload["customer"] = customer
        response = self.client_a.post(API + "sales/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()
