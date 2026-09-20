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

    def test_deleting_customer_keeps_sales(self):
        omar = self.client_a.post(API + "customers/", {"name": "Omar"}, format="json").json()
        sale = self.make_sale(self.make_product()["id"], quantity=1, customer=omar["id"])
        self.client_a.delete(API + f"customers/{omar['id']}/")
        kept = self.client_a.get(API + f"sales/{sale['id']}/").json()
        self.assertIsNone(kept["customer"])


class CustomerSearchAndOrderingTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        for name in ("Sara Ali", "Omar Khaled", "Ahmad Omar"):
            self.client_a.post(API + "customers/", {"name": name}, format="json")

    def names(self, client, query=""):
        response = client.get(API + "customers/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return [c["name"] for c in response.json()]

    def test_default_order_is_by_name(self):
        self.assertEqual(self.names(self.client_a), ["Ahmad Omar", "Omar Khaled", "Sara Ali"])

    def test_search_by_name_is_case_insensitive_and_partial(self):
        self.assertEqual(self.names(self.client_a, "?search=omar"), ["Ahmad Omar", "Omar Khaled"])
        self.assertEqual(self.names(self.client_a, "?search=sara"), ["Sara Ali"])
        self.assertEqual(self.names(self.client_a, "?search=nobody"), [])

    def test_ordering(self):
        self.assertEqual(self.names(self.client_a, "?ordering=-name"), ["Sara Ali", "Omar Khaled", "Ahmad Omar"])

    def test_search_and_ordering_combine(self):
        self.assertEqual(self.names(self.client_a, "?search=omar&ordering=-name"), ["Omar Khaled", "Ahmad Omar"])

    def test_search_never_reaches_another_business(self):
        self.assertEqual(self.names(self.client_b, "?search=omar"), [])
        self.client_b.post(API + "customers/", {"name": "Omar B"}, format="json")
        self.assertEqual(self.names(self.client_b, "?search=omar"), ["Omar B"])
        self.assertEqual(self.names(self.client_b), ["Omar B"])


class CustomerHistoryTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.omar = self.client_a.post(API + "customers/", {"name": "Omar"}, format="json").json()
        self.product = self.make_product(selling_price="10.00", initial_quantity=1000)

    def history(self, customer_id=None, client=None):
        response = (client or self.client_a).get(API + f"customers/{customer_id or self.omar['id']}/history/")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def sell(self, quantity, paid="0", customer=None):
        return self.make_sale(self.product["id"], quantity=quantity, paid=paid, customer=customer or self.omar["id"])

    def pay(self, sale, amount):
        response = self.client_a.post(
            API + f"sales/{sale['id']}/payments/", {"amount": amount, "payment_method": "CASH"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)

    def assert_summary(self, body, purchases, paid, outstanding):
        self.assertEqual(
            body["summary"],
            {"total_purchases": purchases, "total_paid": paid, "outstanding_balance": outstanding},
        )

    def test_response_shape(self):
        sale = self.sell(2, paid="5.00")
        body = self.history()
        self.assertEqual(set(body), {"customer", "summary", "sales"})
        self.assertEqual(body["customer"]["id"], self.omar["id"])
        self.assertEqual(body["customer"]["name"], "Omar")
        self.assertEqual([s["id"] for s in body["sales"]], [sale["id"]])
        self.assertEqual(body["sales"][0]["items"][0]["unit_price"], "10.00")

    def test_customer_with_no_sales(self):
        body = self.history()
        self.assert_summary(body, "0.00", "0.00", "0.00")
        self.assertEqual(body["sales"], [])

    def test_one_unpaid_sale(self):
        self.sell(5)
        self.assert_summary(self.history(), "50.00", "0.00", "50.00")

    def test_partially_paid_sale(self):
        self.sell(5, paid="20.00")
        self.assert_summary(self.history(), "50.00", "20.00", "30.00")

    def test_fully_paid_sale(self):
        self.sell(5, paid="50.00")
        self.assert_summary(self.history(), "50.00", "50.00", "0.00")

    def test_multiple_sales_are_added_up(self):
        self.sell(5, paid="50.00")   # paid
        self.sell(3, paid="10.00")   # partial: 30, paid 10
        self.sell(2)                 # unpaid: 20
        body = self.history()
        self.assert_summary(body, "100.00", "60.00", "40.00")
        self.assertEqual(len(body["sales"]), 3)

    def test_summary_follows_payments_made_later(self):
        sale = self.sell(5)
        self.pay(sale, "20.00")
        self.assert_summary(self.history(), "50.00", "20.00", "30.00")
        self.pay(sale, "30.00")
        self.assert_summary(self.history(), "50.00", "50.00", "0.00")

    def test_summary_follows_edited_sales(self):
        sale = self.sell(5, paid="20.00")
        self.client_a.patch(
            API + f"sales/{sale['id']}/", {"items": [{"product": self.product["id"], "quantity": 8}]}, format="json"
        )
        self.assert_summary(self.history(), "80.00", "20.00", "60.00")

    def test_summary_follows_deleted_sales(self):
        keep = self.sell(1, paid="10.00")
        gone = self.sell(4, paid="15.00")
        self.assert_summary(self.history(), "50.00", "25.00", "25.00")
        self.client_a.delete(API + f"sales/{gone['id']}/")
        body = self.history()
        self.assert_summary(body, "10.00", "10.00", "0.00")
        self.assertEqual([s["id"] for s in body["sales"]], [keep["id"]])

    def test_sales_are_newest_first(self):
        first = self.sell(1)
        second = self.sell(1)
        self.assertEqual([s["id"] for s in self.history()["sales"]], [second["id"], first["id"]])

    def test_sales_of_other_customers_are_not_included(self):
        sara = self.client_a.post(API + "customers/", {"name": "Sara"}, format="json").json()
        self.sell(1, paid="10.00")
        self.sell(7, customer=sara["id"])
        self.assert_summary(self.history(), "10.00", "10.00", "0.00")
        self.assert_summary(self.history(sara["id"]), "70.00", "0.00", "70.00")

    def test_customer_of_another_business_is_404(self):
        self.sell(1)
        response = self.client_b.get(API + f"customers/{self.omar['id']}/history/")
        self.assertEqual(response.status_code, 404)

    def test_unknown_customer_is_404(self):
        self.assertEqual(self.client_a.get(API + "customers/99999/history/").status_code, 404)

    def test_isolation_between_businesses(self):
        self.sell(5, paid="10.00")
        bob = self.client_b.post(API + "customers/", {"name": "Bob"}, format="json").json()
        product_b = self.make_product(client=self.client_b, selling_price="3.00", initial_quantity=100)
        self.make_sale(product_b["id"], quantity=2, paid="1.00", customer=bob["id"], client=self.client_b)
        self.assert_summary(self.history(), "50.00", "10.00", "40.00")
        self.assert_summary(self.history(bob["id"], client=self.client_b), "6.00", "1.00", "5.00")
