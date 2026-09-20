from decimal import Decimal

from .base import API, BusinessAPITestCase


class SaleTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product()  # price 2.50, quantity 10

    def stock(self):
        return self.client_a.get(API + f"products/{self.product['id']}/").json()["quantity"]

    def test_create_deducts_stock_and_computes_status(self):
        sale = self.make_sale(self.product["id"], quantity=4, paid="5.00")
        self.assertEqual(sale["total_amount"], "10.00")
        self.assertEqual(sale["remaining_amount"], "5.00")
        self.assertEqual(sale["payment_status"], "PARTIAL")
        self.assertEqual(self.stock(), 6)
        paid = self.make_sale(self.product["id"], quantity=1, paid="2.50")
        self.assertEqual(paid["payment_status"], "PAID")
        unpaid = self.make_sale(self.product["id"], quantity=1)
        self.assertEqual(unpaid["payment_status"], "UNPAID")

    def test_validation_errors_do_not_change_stock(self):
        pid = self.product["id"]
        bad = [
            {"items": [{"product": pid, "quantity": 9999}]},
            {"items": []},
            {"items": [{"product": pid, "quantity": 0}]},
            {"paid_amount": "9999", "items": [{"product": pid, "quantity": 1}]},
            {"customer": 9999, "items": [{"product": pid, "quantity": 1}]},
            {"items": [{"product": 9999, "quantity": 1}]},
        ]
        for body in bad:
            self.assertEqual(self.client_a.post(API + "sales/", body, format="json").status_code, 400, body)
        self.assertEqual(self.stock(), 10)

    def test_delete_restores_stock(self):
        sale = self.make_sale(self.product["id"], quantity=4)
        self.assertEqual(self.stock(), 6)
        self.assertEqual(self.client_a.delete(API + f"sales/{sale['id']}/").status_code, 204)
        self.assertEqual(self.stock(), 10)

    def test_update_items_restocks_and_reprices(self):
        sale = self.make_sale(self.product["id"], quantity=4)
        response = self.client_a.patch(
            API + f"sales/{sale['id']}/",
            {"items": [{"product": self.product["id"], "quantity": 2}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_amount"], "5.00")
        self.assertEqual(self.stock(), 8)

    def test_update_cannot_reduce_total_below_paid_amount(self):
        sale = self.make_sale(self.product["id"], quantity=4, paid="10.00")
        response = self.client_a.patch(
            API + f"sales/{sale['id']}/",
            {"items": [{"product": self.product["id"], "quantity": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        # the failed edit is rolled back: stock and sale are unchanged
        self.assertEqual(self.stock(), 6)
        unchanged = self.client_a.get(API + f"sales/{sale['id']}/").json()
        self.assertEqual(unchanged["total_amount"], "10.00")
        self.assertEqual(unchanged["remaining_amount"], "0.00")

    def test_update_paid_amount_recomputes_status(self):
        sale = self.make_sale(self.product["id"], quantity=4)
        response = self.client_a.patch(API + f"sales/{sale['id']}/", {"paid_amount": "10.00"}, format="json")
        self.assertEqual(response.json()["payment_status"], "PAID")
        too_much = self.client_a.patch(API + f"sales/{sale['id']}/", {"paid_amount": "99"}, format="json")
        self.assertEqual(too_much.status_code, 400)


class PaymentTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.sale = self.make_sale(self.make_product()["id"], quantity=4, paid="5.00")
        self.url = API + f"sales/{self.sale['id']}/payments/"

    def sale_now(self):
        return self.client_a.get(API + f"sales/{self.sale['id']}/").json()

    def test_partial_then_full_payment(self):
        first = self.client_a.post(self.url, {"amount": "2.00", "payment_method": "CARD", "note": "x"}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["payment_method"], "CARD")
        self.assertEqual(self.sale_now()["payment_status"], "PARTIAL")
        self.client_a.post(self.url, {"amount": "3.00", "payment_method": "CASH"}, format="json")
        now = self.sale_now()
        self.assertEqual(now["payment_status"], "PAID")
        self.assertEqual(Decimal(now["remaining_amount"]), Decimal("0"))

    def test_payment_method_defaults_to_cash(self):
        response = self.client_a.post(self.url, {"amount": "1.00"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["payment_method"], "CASH")

    def test_invalid_payments_are_400(self):
        for body in (
            {"amount": "999", "payment_method": "CASH"},
            {"amount": "0", "payment_method": "CASH"},
            {"amount": "-3", "payment_method": "CASH"},
            {"amount": "1", "payment_method": "BTC"},
            {"payment_method": "CASH"},
        ):
            self.assertEqual(self.client_a.post(self.url, body, format="json").status_code, 400, body)
        self.assertEqual(self.sale_now()["paid_amount"], "5.00")
