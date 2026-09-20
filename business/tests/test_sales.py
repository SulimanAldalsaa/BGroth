from decimal import Decimal

from .base import API, BusinessAPITestCase, utc


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

    def test_update_items_restocks_and_recalculates_total(self):
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

    def test_update_items_recalculates_status_from_existing_payments(self):
        sale = self.make_sale(self.product["id"], quantity=4, paid="5.00")  # total 10, PARTIAL
        pid = self.product["id"]
        smaller = self.client_a.patch(
            API + f"sales/{sale['id']}/", {"items": [{"product": pid, "quantity": 2}]}, format="json"
        ).json()
        self.assertEqual(smaller["total_amount"], "5.00")
        self.assertEqual(smaller["paid_amount"], "5.00")
        self.assertEqual(smaller["remaining_amount"], "0.00")
        self.assertEqual(smaller["payment_status"], "PAID")
        bigger = self.client_a.patch(
            API + f"sales/{sale['id']}/", {"items": [{"product": pid, "quantity": 6}]}, format="json"
        ).json()
        self.assertEqual(bigger["total_amount"], "15.00")
        self.assertEqual(bigger["paid_amount"], "5.00")
        self.assertEqual(bigger["remaining_amount"], "10.00")
        self.assertEqual(bigger["payment_status"], "PARTIAL")

    def test_update_customer_only_keeps_items_and_payments(self):
        omar = self.client_a.post(API + "customers/", {"name": "Omar"}, format="json").json()
        sale = self.make_sale(self.product["id"], quantity=4, paid="5.00")
        updated = self.client_a.patch(API + f"sales/{sale['id']}/", {"customer": omar["id"]}, format="json")
        self.assertEqual(updated.status_code, 200)
        body = updated.json()
        self.assertEqual(body["customer"], omar["id"])
        self.assertEqual(body["items"], sale["items"])
        self.assertEqual(body["paid_amount"], "5.00")
        self.assertEqual(body["payment_status"], "PARTIAL")
        self.assertEqual(self.stock(), 6)


class SalePaymentsAreNotEditableTests(BusinessAPITestCase):
    """Payments are recorded only through POST /sales/{id}/payments/."""

    def setUp(self):
        super().setUp()
        self.product = self.make_product()
        self.sale = self.make_sale(self.product["id"], quantity=4, paid="2.00")
        self.url = API + f"sales/{self.sale['id']}/"

    def assert_sale_unchanged(self):
        now = self.client_a.get(self.url).json()
        self.assertEqual(now["paid_amount"], "2.00")
        self.assertEqual(now["remaining_amount"], "8.00")
        self.assertEqual(now["payment_status"], "PARTIAL")
        self.assertEqual(now["total_amount"], "10.00")

    def test_patch_with_paid_amount_is_rejected(self):
        response = self.client_a.patch(self.url, {"paid_amount": "10.00"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("paid_amount", response.json())
        self.assert_sale_unchanged()

    def test_put_with_paid_amount_is_rejected(self):
        response = self.client_a.put(self.url, {"paid_amount": "10.00"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assert_sale_unchanged()

    def test_derived_money_fields_cannot_be_edited(self):
        for field, value in (
            ("payment_status", "PAID"),
            ("remaining_amount", "0.00"),
            ("total_amount", "1.00"),
        ):
            response = self.client_a.patch(self.url, {field: value}, format="json")
            self.assertEqual(response.status_code, 400, field)
            self.assertIn(field, response.json())
        self.assert_sale_unchanged()

    def test_rejected_edit_does_not_apply_other_fields(self):
        response = self.client_a.patch(
            self.url,
            {"paid_amount": "10.00", "items": [{"product": self.product["id"], "quantity": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assert_sale_unchanged()
        stock = self.client_a.get(API + f"products/{self.product['id']}/").json()["quantity"]
        self.assertEqual(stock, 6)

    def test_payment_endpoint_still_updates_the_sale(self):
        self.client_a.post(self.url + "payments/", {"amount": "3.00", "payment_method": "CASH"}, format="json")
        partial = self.client_a.get(self.url).json()
        self.assertEqual(partial["paid_amount"], "5.00")
        self.assertEqual(partial["payment_status"], "PARTIAL")
        self.client_a.post(self.url + "payments/", {"amount": "5.00", "payment_method": "CARD"}, format="json")
        paid = self.client_a.get(self.url).json()
        self.assertEqual(paid["paid_amount"], "10.00")
        self.assertEqual(paid["remaining_amount"], "0.00")
        self.assertEqual(paid["payment_status"], "PAID")


class SaleHistoricalPriceTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product(name="Cola", selling_price="10.00", initial_quantity=100)
        self.pid = self.product["id"]
        self.sale = self.make_sale(self.pid, quantity=2)
        self.url = API + f"sales/{self.sale['id']}/"

    def set_price(self, product_id, price):
        response = self.client_a.patch(API + f"products/{product_id}/", {"selling_price": price}, format="json")
        self.assertEqual(response.status_code, 200)

    def stock(self, product_id):
        return self.client_a.get(API + f"products/{product_id}/").json()["quantity"]

    def test_changing_product_price_does_not_change_existing_sale(self):
        self.assertEqual(self.sale["items"][0]["unit_price"], "10.00")
        self.assertEqual(self.sale["total_amount"], "20.00")
        self.set_price(self.pid, "20.00")
        sale = self.client_a.get(self.url).json()
        self.assertEqual(sale["items"][0]["unit_price"], "10.00")
        self.assertEqual(sale["items"][0]["subtotal"], "20.00")
        self.assertEqual(sale["total_amount"], "20.00")
        listed = self.client_a.get(API + "sales/").json()
        self.assertEqual(listed[0]["items"][0]["unit_price"], "10.00")

    def test_new_sales_use_the_new_price(self):
        self.set_price(self.pid, "20.00")
        newer = self.make_sale(self.pid, quantity=1)
        self.assertEqual(newer["items"][0]["unit_price"], "20.00")
        self.assertEqual(newer["total_amount"], "20.00")

    def test_updating_quantity_keeps_the_historical_price(self):
        self.set_price(self.pid, "20.00")
        response = self.client_a.patch(
            self.url, {"items": [{"product": self.pid, "quantity": 3}]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["unit_price"], "10.00")
        self.assertEqual(item["subtotal"], "30.00")
        self.assertEqual(response.json()["total_amount"], "30.00")
        # stock: 100 - 2 sold, then the edit restores 2 and deducts 3
        self.assertEqual(self.stock(self.pid), 97)

    def test_added_product_uses_current_price_and_old_items_are_not_repriced(self):
        other = self.make_product(name="Chips", selling_price="7.00", initial_quantity=50)
        self.set_price(self.pid, "20.00")
        response = self.client_a.patch(
            self.url,
            {"items": [
                {"product": self.pid, "quantity": 2},
                {"product": other["id"], "quantity": 1},
            ]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        prices = {i["product"]: i["unit_price"] for i in response.json()["items"]}
        self.assertEqual(prices, {self.pid: "10.00", other["id"]: "7.00"})
        self.assertEqual(response.json()["total_amount"], "27.00")
        self.assertEqual(self.stock(self.pid), 98)
        self.assertEqual(self.stock(other["id"]), 49)

    def test_removed_item_restores_stock(self):
        other = self.make_product(name="Chips", selling_price="7.00", initial_quantity=50)
        response = self.client_a.patch(
            self.url, {"items": [{"product": other["id"], "quantity": 5}]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_amount"], "35.00")
        self.assertEqual(self.stock(self.pid), 100)
        self.assertEqual(self.stock(other["id"]), 45)


class SaleListQueryTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.early = self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 1))
        self.middle = self.make_sale_at(self.user_a, "30.00", utc(2026, 9, 10))
        self.late = self.make_sale_at(self.user_a, "20.00", utc(2026, 9, 20))

    def ids(self, query=""):
        response = self.client_a.get(API + "sales/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return [sale["id"] for sale in response.json()]

    def test_default_order_is_newest_first(self):
        self.assertEqual(self.ids(), [self.late.id, self.middle.id, self.early.id])

    def test_date_from(self):
        self.assertEqual(self.ids("?date_from=2026-09-10"), [self.late.id, self.middle.id])

    def test_date_to(self):
        self.assertEqual(self.ids("?date_to=2026-09-10"), [self.middle.id, self.early.id])

    def test_date_from_and_date_to(self):
        self.assertEqual(self.ids("?date_from=2026-09-05&date_to=2026-09-15"), [self.middle.id])
        self.assertEqual(self.ids("?date_from=2026-09-10&date_to=2026-09-10"), [self.middle.id])

    def test_range_is_inclusive_for_the_whole_day(self):
        last_second = self.make_sale_at(self.user_a, "1.00", utc(2026, 9, 10, 23, 59, 59))
        next_day = self.make_sale_at(self.user_a, "1.00", utc(2026, 9, 11, 0, 0, 0))
        result = self.ids("?date_from=2026-09-10&date_to=2026-09-10")
        self.assertIn(last_second.id, result)
        self.assertNotIn(next_day.id, result)

    def test_blank_date_parameters_are_ignored(self):
        self.assertEqual(
            self.ids("?date_from=&date_to="), [self.late.id, self.middle.id, self.early.id]
        )

    def test_no_match_returns_empty_list(self):
        self.assertEqual(self.ids("?date_from=2027-01-01"), [])

    def test_invalid_dates_return_400_naming_the_parameter(self):
        for query, field in (
            ("?date_from=not-a-date", "date_from"),
            ("?date_to=2026-13-45", "date_to"),
            ("?date_from=2026-09-20&date_to=2026-09-01", "date_to"),
        ):
            response = self.client_a.get(API + "sales/" + query)
            self.assertEqual(response.status_code, 400, query)
            self.assertIn(field, response.json(), query)

    def test_filtering_never_returns_another_business(self):
        other = self.make_sale_at(self.user_b, "99.00", utc(2026, 9, 10))
        self.assertNotIn(other.id, self.ids("?date_from=2026-09-01&date_to=2026-09-30"))
        response = self.client_b.get(API + "sales/?date_from=2026-09-01&date_to=2026-09-30")
        self.assertEqual([s["id"] for s in response.json()], [other.id])

    def test_ordering(self):
        self.assertEqual(self.ids("?ordering=total_amount"), [self.early.id, self.late.id, self.middle.id])
        self.assertEqual(self.ids("?ordering=-total_amount"), [self.middle.id, self.late.id, self.early.id])
        self.assertEqual(self.ids("?ordering=sold_at"), [self.early.id, self.middle.id, self.late.id])

    def test_ordering_works_together_with_date_filter(self):
        self.assertEqual(
            self.ids("?date_from=2026-09-10&ordering=total_amount"), [self.late.id, self.middle.id]
        )

    def test_unknown_ordering_field_falls_back_to_default(self):
        self.assertEqual(self.ids("?ordering=business__name"), [self.late.id, self.middle.id, self.early.id])

    def test_without_page_parameters_the_response_is_a_plain_array(self):
        self.assertIsInstance(self.client_a.get(API + "sales/").json(), list)

    def test_pagination(self):
        first = self.client_a.get(API + "sales/?page_size=2").json()
        self.assertEqual(first["count"], 3)
        self.assertIsNotNone(first["next"])
        self.assertIsNone(first["previous"])
        self.assertEqual([s["id"] for s in first["results"]], [self.late.id, self.middle.id])
        second = self.client_a.get(API + "sales/?page=2&page_size=2").json()
        self.assertEqual([s["id"] for s in second["results"]], [self.early.id])
        self.assertIsNone(second["next"])

    def test_pagination_keeps_filters_and_ordering(self):
        body = self.client_a.get(API + "sales/?date_from=2026-09-10&ordering=total_amount&page_size=1").json()
        self.assertEqual(body["count"], 2)
        self.assertEqual([s["id"] for s in body["results"]], [self.late.id])

    def test_pages_do_not_overlap_when_values_tie(self):
        for _ in range(4):
            self.make_sale_at(self.user_a, "5.00", utc(2026, 9, 5))
        seen = []
        for page in range(1, 4):
            body = self.client_a.get(API + f"sales/?ordering=total_amount&page={page}&page_size=3").json()
            seen += [s["id"] for s in body["results"]]
        self.assertEqual(len(seen), 7)
        self.assertEqual(len(set(seen)), 7)

    def test_pagination_only_counts_own_sales(self):
        self.make_sale_at(self.user_b, "1.00", utc(2026, 9, 10))
        self.assertEqual(self.client_a.get(API + "sales/?page_size=1").json()["count"], 3)

    def test_page_beyond_the_end_is_404(self):
        self.assertEqual(self.client_a.get(API + "sales/?page=99").status_code, 404)

    def test_page_size_is_capped(self):
        body = self.client_a.get(API + "sales/?page_size=1000").json()
        self.assertEqual(body["count"], 3)
        self.assertEqual(len(body["results"]), 3)


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
