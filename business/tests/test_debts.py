from datetime import date, timedelta
from unittest.mock import patch

from rest_framework.test import APIClient

from .base import API, BusinessAPITestCase

TODAY = date(2026, 9, 24)
PATCH_TODAY = patch("business.selectors.debt_selectors.timezone.localdate", return_value=TODAY)


class DebtCreationTests(BusinessAPITestCase):
    def test_create_payable_debt(self):
        response = self.client_a.post(
            API + "debts/",
            {
                "debt_type": "PAYABLE",
                "party_name": "Supplier A",
                "original_amount": "500.00",
                "due_date": "2026-10-01",
                "notes": "October stock",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual(body["debt_type"], "PAYABLE")
        self.assertEqual(body["party_name"], "Supplier A")
        self.assertEqual(body["original_amount"], "500.00")
        self.assertEqual(body["paid_amount"], "0.00")
        self.assertEqual(body["remaining_amount"], "500.00")
        self.assertEqual(body["status"], "UNPAID")

    def test_create_receivable_debt(self):
        customer = self.client_a.post(API + "customers/", {"name": "Sara"}, format="json").json()
        response = self.client_a.post(
            API + "debts/",
            {
                "debt_type": "RECEIVABLE",
                "party_name": "Sara",
                "customer": customer["id"],
                "original_amount": "80.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["customer"], customer["id"])

    def test_invalid_debt_type_is_rejected(self):
        response = self.client_a.post(
            API + "debts/",
            {"debt_type": "LOAN", "party_name": "X", "original_amount": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("debt_type", response.json())

    def test_missing_debt_type_is_rejected(self):
        response = self.client_a.post(
            API + "debts/",
            {"party_name": "X", "original_amount": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("debt_type", response.json())

    def test_negative_original_amount_is_rejected(self):
        response = self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "X", "original_amount": "-5.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("original_amount", response.json())

    def test_unauthenticated_user_gets_401(self):
        response = APIClient().post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "X", "original_amount": "10.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_customer_is_rejected(self):
        response = self.client_a.post(
            API + "debts/",
            {
                "debt_type": "RECEIVABLE",
                "party_name": "X",
                "customer": 999999,
                "original_amount": "10.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_foreign_customer_is_rejected(self):
        other_customer = self.client_b.post(
            API + "customers/", {"name": "B's customer"}, format="json"
        ).json()
        response = self.client_a.post(
            API + "debts/",
            {
                "debt_type": "RECEIVABLE",
                "party_name": "X",
                "customer": other_customer["id"],
                "original_amount": "10.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class DebtPaymentTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.debt = self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "Supplier A", "original_amount": "100.00"},
            format="json",
        ).json()
        self.url = API + f"debts/{self.debt['id']}/payments/"

    def debt_now(self):
        return self.client_a.get(API + f"debts/{self.debt['id']}/").json()

    def test_unpaid_to_partial(self):
        response = self.client_a.post(self.url, {"amount": "40.00"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        debt = self.debt_now()
        self.assertEqual(debt["paid_amount"], "40.00")
        self.assertEqual(debt["remaining_amount"], "60.00")
        self.assertEqual(debt["status"], "PARTIAL")

    def test_multiple_partial_payments_then_exact_final_payment_is_paid(self):
        self.client_a.post(self.url, {"amount": "30.00"}, format="json")
        self.client_a.post(self.url, {"amount": "20.00"}, format="json")
        mid = self.debt_now()
        self.assertEqual(mid["paid_amount"], "50.00")
        self.assertEqual(mid["status"], "PARTIAL")

        final = self.client_a.post(self.url, {"amount": "50.00"}, format="json")
        self.assertEqual(final.status_code, 201)
        debt = self.debt_now()
        self.assertEqual(debt["paid_amount"], "100.00")
        self.assertEqual(debt["remaining_amount"], "0.00")
        self.assertEqual(debt["status"], "PAID")

    def test_negative_payment_is_rejected(self):
        response = self.client_a.post(self.url, {"amount": "-5.00"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_zero_payment_is_rejected(self):
        response = self.client_a.post(self.url, {"amount": "0.00"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_payment_cannot_exceed_remaining_balance(self):
        response = self.client_a.post(self.url, {"amount": "150.00"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"detail": "Payment cannot exceed remaining amount."}
        )
        self.assertEqual(self.debt_now()["paid_amount"], "0.00")

    def test_payment_on_foreign_debt_is_404(self):
        response = self.client_b.post(self.url, {"amount": "10.00"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_paid_amount_cannot_be_set_directly_via_patch(self):
        response = self.client_a.patch(
            API + f"debts/{self.debt['id']}/", {"paid_amount": "100.00"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("paid_amount", response.json())
        self.assertEqual(self.debt_now()["paid_amount"], "0.00")


class DebtUpdateTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.debt = self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "Supplier A", "original_amount": "100.00"},
            format="json",
        ).json()
        self.url = API + f"debts/{self.debt['id']}/"

    def test_can_update_party_name_due_date_and_notes(self):
        response = self.client_a.patch(
            self.url,
            {"party_name": "Supplier B", "due_date": "2026-11-01", "notes": "updated"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["party_name"], "Supplier B")
        self.assertEqual(body["due_date"], "2026-11-01")
        self.assertEqual(body["notes"], "updated")

    def test_cannot_change_debt_type(self):
        response = self.client_a.patch(self.url, {"debt_type": "RECEIVABLE"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("debt_type", response.json())

    def test_delete_is_not_supported(self):
        # BR-9: no destructive deletion is exposed for debts in this sprint.
        self.assertEqual(self.client_a.delete(self.url).status_code, 405)

    def test_foreign_debt_update_is_404(self):
        response = self.client_b.patch(self.url, {"notes": "x"}, format="json")
        self.assertEqual(response.status_code, 404)


class DebtDueListTests(BusinessAPITestCase):
    def make_debt(self, due_date=None, amount="100.00", client=None):
        payload = {"debt_type": "PAYABLE", "party_name": "S", "original_amount": amount}
        if due_date:
            payload["due_date"] = due_date.isoformat()
        return (client or self.client_a).post(API + "debts/", payload, format="json").json()

    def due(self, query="", client=None):
        with PATCH_TODAY:
            response = (client or self.client_a).get(API + "debts/due/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return [d["id"] for d in response.json()]

    def test_due_within_window_is_included(self):
        due_soon = self.make_debt(due_date=TODAY + timedelta(days=3))
        due_later = self.make_debt(due_date=TODAY + timedelta(days=30))
        no_due_date = self.make_debt(due_date=None)

        ids = self.due("?days=7")
        self.assertIn(due_soon["id"], ids)
        self.assertNotIn(due_later["id"], ids)
        self.assertNotIn(no_due_date["id"], ids)

    def test_overdue_debts_are_excluded(self):
        overdue = self.make_debt(due_date=TODAY - timedelta(days=1))
        self.assertNotIn(overdue["id"], self.due("?days=7"))

    def test_paid_debts_are_excluded(self):
        debt = self.make_debt(due_date=TODAY + timedelta(days=1))
        self.client_a.post(
            API + f"debts/{debt['id']}/payments/", {"amount": "100.00"}, format="json"
        )
        self.assertNotIn(debt["id"], self.due("?days=7"))

    def test_default_window_is_seven_days(self):
        due_soon = self.make_debt(due_date=TODAY + timedelta(days=5))
        due_later = self.make_debt(due_date=TODAY + timedelta(days=10))
        ids = self.due()
        self.assertIn(due_soon["id"], ids)
        self.assertNotIn(due_later["id"], ids)

    def test_isolated_per_business(self):
        mine = self.make_debt(due_date=TODAY + timedelta(days=1))
        self.make_debt(due_date=TODAY + timedelta(days=1), client=self.client_b)
        self.assertEqual(self.due("?days=7"), [mine["id"]])


class DebtFilterTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.payable = self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "Supplier A", "original_amount": "50.00"},
            format="json",
        ).json()
        self.receivable = self.client_a.post(
            API + "debts/",
            {"debt_type": "RECEIVABLE", "party_name": "Customer B", "original_amount": "30.00"},
            format="json",
        ).json()

    def ids(self, query=""):
        response = self.client_a.get(API + "debts/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return [d["id"] for d in response.json()]

    def test_filter_by_type(self):
        self.assertEqual(self.ids("?type=PAYABLE"), [self.payable["id"]])
        self.assertEqual(self.ids("?type=RECEIVABLE"), [self.receivable["id"]])

    def test_filter_by_status(self):
        self.client_a.post(
            API + f"debts/{self.payable['id']}/payments/", {"amount": "50.00"}, format="json"
        )
        self.assertEqual(self.ids("?status=PAID"), [self.payable["id"]])
        self.assertEqual(self.ids("?status=UNPAID"), [self.receivable["id"]])

    def test_search_by_party_name(self):
        self.assertEqual(self.ids("?search=Supplier"), [self.payable["id"]])

    def test_invalid_due_before_returns_400(self):
        response = self.client_a.get(API + "debts/?due_before=not-a-date")
        self.assertEqual(response.status_code, 400)
        self.assertIn("due_before", response.json())


class DebtIsolationTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.debt = self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "Supplier A", "original_amount": "50.00"},
            format="json",
        ).json()

    def test_user_b_cannot_list_user_a_debt(self):
        ids = [d["id"] for d in self.client_b.get(API + "debts/").json()]
        self.assertNotIn(self.debt["id"], ids)

    def test_user_b_cannot_retrieve_user_a_debt(self):
        response = self.client_b.get(API + f"debts/{self.debt['id']}/")
        self.assertEqual(response.status_code, 404)

    def test_user_b_cannot_pay_user_a_debt(self):
        response = self.client_b.post(
            API + f"debts/{self.debt['id']}/payments/", {"amount": "10.00"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
