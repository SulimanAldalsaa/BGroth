from .base import API, BusinessAPITestCase


class ProductTests(BusinessAPITestCase):
    def test_create_with_initial_quantity_and_validation(self):
        product = self.make_product()
        self.assertEqual(product["quantity"], 10)
        missing = self.client_a.post(API + "products/", {"name": "X"}, format="json")
        self.assertEqual(missing.status_code, 400)
        negative = self.client_a.post(
            API + "products/", {"name": "X", "selling_price": "-1"}, format="json"
        )
        self.assertEqual(negative.status_code, 400)

    def test_quantity_is_read_only_on_update(self):
        product = self.make_product()
        response = self.client_a.patch(
            API + f"products/{product['id']}/", {"quantity": 999}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["quantity"], 10)

    def test_adjust_stock_in_out_and_set(self):
        pid = self.make_product()["id"]
        url = API + f"products/{pid}/adjust-stock/"
        self.assertEqual(
            self.client_a.post(url, {"quantity": 5, "movement_type": "IN"}, format="json").json()["quantity"], 15
        )
        self.assertEqual(
            self.client_a.post(url, {"quantity": 3, "movement_type": "OUT"}, format="json").json()["quantity"], 12
        )
        self.assertEqual(
            self.client_a.post(url, {"quantity": 7, "movement_type": "ADJUSTMENT"}, format="json").json()["quantity"], 7
        )

    def test_adjust_stock_rejects_bad_input_without_500(self):
        pid = self.make_product()["id"]
        url = API + f"products/{pid}/adjust-stock/"
        cases = [
            {"quantity": 999, "movement_type": "OUT"},
            {"quantity": -5, "movement_type": "ADJUSTMENT"},
            {"quantity": "abc", "movement_type": "IN"},
            {"quantity": 1, "movement_type": "FOO"},
            {"quantity": 1, "movement_type": "SALE"},
            {"movement_type": "IN"},
        ]
        for body in cases:
            self.assertEqual(self.client_a.post(url, body, format="json").status_code, 400, body)
        unknown = self.client_a.post(
            API + "products/99999/adjust-stock/", {"quantity": 1, "movement_type": "IN"}, format="json"
        )
        self.assertEqual(unknown.status_code, 404)

    def test_low_stock_and_out_of_stock(self):
        low = self.make_product(name="Low", initial_quantity=2, minimum_stock=3)
        empty = self.make_product(name="Empty", initial_quantity=0, minimum_stock=0)
        self.make_product(name="Plenty", initial_quantity=50, minimum_stock=3)
        low_ids = {p["id"] for p in self.client_a.get(API + "products/low-stock/").json()}
        out_ids = {p["id"] for p in self.client_a.get(API + "products/out-of-stock/").json()}
        self.assertEqual(low_ids, {low["id"], empty["id"]})
        self.assertEqual(out_ids, {empty["id"]})

    def test_delete_unsold_product_ok_sold_product_is_400(self):
        unsold = self.make_product(name="Unsold")
        self.assertEqual(self.client_a.delete(API + f"products/{unsold['id']}/").status_code, 204)
        sold = self.make_product(name="Sold")
        self.make_sale(sold["id"], quantity=1)
        response = self.client_a.delete(API + f"products/{sold['id']}/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())
