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


class ProductSearchAndOrderingTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.cola = self.make_product(name="Cola Zero", selling_price="3.00", initial_quantity=5)
        self.chips = self.make_product(name="Chips", selling_price="1.50", initial_quantity=50)
        self.water = self.make_product(name="Cola Water", selling_price="1.00", initial_quantity=20)

    def names(self, query="", client=None):
        response = (client or self.client_a).get(API + "products/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return [p["name"] for p in response.json()]

    def test_default_order_is_by_name(self):
        self.assertEqual(self.names(), ["Chips", "Cola Water", "Cola Zero"])

    def test_search_by_name_is_case_insensitive_and_partial(self):
        self.assertEqual(self.names("?search=cola"), ["Cola Water", "Cola Zero"])
        self.assertEqual(self.names("?search=CHIP"), ["Chips"])
        self.assertEqual(self.names("?search=zzz"), [])

    def test_ordering(self):
        self.assertEqual(self.names("?ordering=selling_price"), ["Cola Water", "Chips", "Cola Zero"])
        self.assertEqual(self.names("?ordering=-quantity"), ["Chips", "Cola Water", "Cola Zero"])
        self.assertEqual(self.names("?ordering=-name"), ["Cola Zero", "Cola Water", "Chips"])

    def test_search_and_ordering_combine(self):
        self.assertEqual(self.names("?search=cola&ordering=-selling_price"), ["Cola Zero", "Cola Water"])

    def test_search_and_ordering_stay_inside_the_business(self):
        self.assertEqual(self.names("?search=cola", client=self.client_b), [])
        self.make_product(client=self.client_b, name="Cola B", selling_price="9.00")
        self.assertEqual(self.names("?search=cola", client=self.client_b), ["Cola B"])
        self.assertEqual(self.names("?ordering=-selling_price", client=self.client_b), ["Cola B"])
        self.assertEqual(self.names("?search=cola"), ["Cola Water", "Cola Zero"])

    def test_low_stock_lists_are_unaffected(self):
        low = self.client_a.get(API + "products/low-stock/").json()
        self.assertEqual(low, [])
