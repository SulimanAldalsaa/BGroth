from rest_framework.test import APIClient

from .base import API, BusinessAPITestCase


class InvoiceCreationTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product(name="Cola", selling_price="10.00", initial_quantity=50)
        self.customer = self.client_a.post(
            API + "customers/", {"name": "Omar", "phone": "0790000000"}, format="json"
        ).json()
        self.sale = self.make_sale(self.product["id"], quantity=2, customer=self.customer["id"])

    def create_invoice(self, sale_id, client=None, body=None):
        return (client or self.client_a).post(
            API + f"sales/{sale_id}/invoice/", body or {}, format="json"
        )

    def test_authenticated_user_can_create_invoice_from_own_sale(self):
        response = self.create_invoice(self.sale["id"])
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["sale"], self.sale["id"])
        self.assertEqual(body["status"], "ISSUED")
        self.assertEqual(body["customer_name"], "Omar")
        self.assertEqual(body["customer_phone"], "0790000000")
        self.assertEqual(body["total"], "20.00")
        self.assertTrue(body["invoice_number"].startswith("INV-"))
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["product_name"], "Cola")
        self.assertEqual(body["items"][0]["quantity"], 2)
        self.assertEqual(body["items"][0]["unit_price"], "10.00")
        self.assertEqual(body["items"][0]["line_total"], "20.00")

    def test_invoice_without_customer_leaves_snapshot_blank(self):
        bare_sale = self.make_sale(self.product["id"], quantity=1)
        response = self.create_invoice(bare_sale["id"])
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["customer_name"], "")
        self.assertEqual(body["customer_phone"], "")

    def test_unauthenticated_user_gets_401(self):
        response = APIClient().post(API + f"sales/{self.sale['id']}/invoice/", {}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_nonexistent_sale_returns_404(self):
        response = self.create_invoice(999999)
        self.assertEqual(response.status_code, 404)

    def test_foreign_sale_returns_404(self):
        response = self.create_invoice(self.sale["id"], client=self.client_b)
        self.assertEqual(response.status_code, 404)

    def test_duplicate_invoice_is_rejected(self):
        first = self.create_invoice(self.sale["id"])
        self.assertEqual(first.status_code, 201)
        second = self.create_invoice(self.sale["id"])
        self.assertEqual(second.status_code, 400)
        self.assertEqual(
            second.json(), {"detail": "An invoice already exists for this sale."}
        )

    def test_invoice_numbers_are_unique_and_sequential_per_business_per_day(self):
        other_sale = self.make_sale(self.product["id"], quantity=1)
        first = self.create_invoice(self.sale["id"]).json()
        second = self.create_invoice(other_sale["id"]).json()
        self.assertNotEqual(first["invoice_number"], second["invoice_number"])
        today_prefix = first["invoice_number"].rsplit("-", 1)[0]
        self.assertEqual(second["invoice_number"].rsplit("-", 1)[0], today_prefix)
        first_seq = int(first["invoice_number"].rsplit("-", 1)[1])
        second_seq = int(second["invoice_number"].rsplit("-", 1)[1])
        self.assertEqual(second_seq, first_seq + 1)

    def test_can_reissue_after_cancelling_previous_invoice_for_same_sale(self):
        # BR-12: "cancel and reissue" must actually be possible for the same sale.
        first = self.create_invoice(self.sale["id"]).json()
        cancel = self.client_a.post(
            API + f"invoices/{first['id']}/cancel/", {}, format="json"
        )
        self.assertEqual(cancel.status_code, 200)

        second = self.create_invoice(self.sale["id"])
        self.assertEqual(second.status_code, 201, second.content)
        second_body = second.json()
        self.assertNotEqual(second_body["id"], first["id"])
        self.assertNotEqual(second_body["invoice_number"], first["invoice_number"])
        self.assertEqual(second_body["status"], "ISSUED")

        # A third (active) invoice for the same sale is still rejected.
        third = self.create_invoice(self.sale["id"])
        self.assertEqual(third.status_code, 400)
        self.assertEqual(
            third.json(), {"detail": "An invoice already exists for this sale."}
        )

        # Both the cancelled and the reissued invoice remain individually visible.
        cancelled_detail = self.client_a.get(API + f"invoices/{first['id']}/")
        self.assertEqual(cancelled_detail.json()["status"], "CANCELLED")
        active_detail = self.client_a.get(API + f"invoices/{second_body['id']}/")
        self.assertEqual(active_detail.json()["status"], "ISSUED")


class InvoiceSnapshotTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product(name="Cola", selling_price="10.00", initial_quantity=50)
        self.customer = self.client_a.post(
            API + "customers/", {"name": "Omar", "phone": "0790000000"}, format="json"
        ).json()
        self.sale = self.make_sale(self.product["id"], quantity=2, customer=self.customer["id"])
        self.invoice = self.client_a.post(
            API + f"sales/{self.sale['id']}/invoice/", {}, format="json"
        ).json()
        self.url = API + f"invoices/{self.invoice['id']}/"

    def test_changing_product_name_and_price_does_not_affect_invoice(self):
        self.client_a.patch(
            API + f"products/{self.product['id']}/",
            {"name": "Pepsi", "selling_price": "99.00"},
            format="json",
        )
        invoice = self.client_a.get(self.url).json()
        self.assertEqual(invoice["items"][0]["product_name"], "Cola")
        self.assertEqual(invoice["items"][0]["unit_price"], "10.00")
        self.assertEqual(invoice["total"], "20.00")

    def test_changing_customer_name_and_phone_does_not_affect_invoice(self):
        self.client_a.patch(
            API + f"customers/{self.customer['id']}/",
            {"name": "Khalid", "phone": "0791111111"},
            format="json",
        )
        invoice = self.client_a.get(self.url).json()
        self.assertEqual(invoice["customer_name"], "Omar")
        self.assertEqual(invoice["customer_phone"], "0790000000")


class InvoiceImmutabilityTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product()
        self.sale = self.make_sale(self.product["id"], quantity=1)
        self.invoice = self.client_a.post(
            API + f"sales/{self.sale['id']}/invoice/", {}, format="json"
        ).json()
        self.url = API + f"invoices/{self.invoice['id']}/"
        self.cancel_url = API + f"invoices/{self.invoice['id']}/cancel/"

    def test_no_update_endpoint_exists(self):
        self.assertEqual(self.client_a.patch(self.url, {"notes": "x"}, format="json").status_code, 405)
        self.assertEqual(self.client_a.put(self.url, {"notes": "x"}, format="json").status_code, 405)

    def test_cancellation_works(self):
        response = self.client_a.post(self.cancel_url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "CANCELLED")

    def test_second_cancellation_fails(self):
        self.client_a.post(self.cancel_url, {}, format="json")
        second = self.client_a.post(self.cancel_url, {}, format="json")
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.json(), {"detail": "Invoice is already cancelled."})

    def test_cancelled_invoice_remains_accessible(self):
        self.client_a.post(self.cancel_url, {}, format="json")
        response = self.client_a.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "CANCELLED")

    def test_sale_with_invoice_cannot_be_deleted(self):
        response = self.client_a.delete(API + f"sales/{self.sale['id']}/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("invoice", response.json()["detail"])


class InvoicePdfTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product()
        self.sale = self.make_sale(self.product["id"], quantity=1)
        self.invoice = self.client_a.post(
            API + f"sales/{self.sale['id']}/invoice/", {}, format="json"
        ).json()

    def test_pdf_returns_200_with_pdf_content_type(self):
        response = self.client_a.get(API + f"invoices/{self.invoice['id']}/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_foreign_invoice_pdf_returns_404(self):
        response = self.client_b.get(API + f"invoices/{self.invoice['id']}/pdf/")
        self.assertEqual(response.status_code, 404)


class InvoiceIsolationTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.product = self.make_product()
        self.sale = self.make_sale(self.product["id"], quantity=1)
        self.invoice = self.client_a.post(
            API + f"sales/{self.sale['id']}/invoice/", {}, format="json"
        ).json()

    def test_user_b_cannot_list_user_a_invoice(self):
        ids = [inv["id"] for inv in self.client_b.get(API + "invoices/").json()]
        self.assertNotIn(self.invoice["id"], ids)

    def test_user_b_cannot_retrieve_user_a_invoice(self):
        response = self.client_b.get(API + f"invoices/{self.invoice['id']}/")
        self.assertEqual(response.status_code, 404)

    def test_user_b_cannot_cancel_user_a_invoice(self):
        response = self.client_b.post(
            API + f"invoices/{self.invoice['id']}/cancel/", {}, format="json"
        )
        self.assertEqual(response.status_code, 404)
