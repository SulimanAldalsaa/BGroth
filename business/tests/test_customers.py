from .base import API, BusinessAPITestCase


class CustomerTests(BusinessAPITestCase):
    def test_crud(self):
        created = self.client_a.post(API + "customers/", {"name": "Omar", "phone": "0791"}, format="json")
        self.assertEqual(created.status_code, 201)
        cid = created.json()["id"]
        self.assertEqual(self.client_a.get(API + f"customers/{cid}/").json()["phone"], "0791")
        updated = self.client_a.patch(API + f"customers/{cid}/", {"phone": "0792"}, format="json")
        self.assertEqual(updated.json()["phone"], "0792")
        self.assertEqual(self.client_a.delete(API + f"customers/{cid}/").status_code, 204)

    def test_name_is_required(self):
        self.assertEqual(self.client_a.post(API + "customers/", {}, format="json").status_code, 400)

    def test_history_lists_only_that_customers_sales(self):
        omar = self.client_a.post(API + "customers/", {"name": "Omar"}, format="json").json()
        sara = self.client_a.post(API + "customers/", {"name": "Sara"}, format="json").json()
        pid = self.make_product()["id"]
        sale = self.make_sale(pid, quantity=1, customer=omar["id"])
        self.make_sale(pid, quantity=1, customer=sara["id"])
        history = self.client_a.get(API + f"customers/{omar['id']}/history/").json()
        self.assertEqual([s["id"] for s in history], [sale["id"]])

    def test_deleting_customer_keeps_sales(self):
        omar = self.client_a.post(API + "customers/", {"name": "Omar"}, format="json").json()
        sale = self.make_sale(self.make_product()["id"], quantity=1, customer=omar["id"])
        self.client_a.delete(API + f"customers/{omar['id']}/")
        kept = self.client_a.get(API + f"sales/{sale['id']}/").json()
        self.assertIsNone(kept["customer"])
