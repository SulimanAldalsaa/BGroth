from datetime import date
from decimal import Decimal
from unittest.mock import patch

from rest_framework.test import APIClient

from .base import API, BusinessAPITestCase, utc

TODAY = date(2026, 9, 24)  # Thursday; month is 1-30 Sep 2026.
PATCH_TODAY = patch("business.views.report.timezone.localdate", return_value=TODAY)


class PerformanceReportTests(BusinessAPITestCase):
    def report(self, query="", client=None):
        with PATCH_TODAY:
            response = (client or self.client_a).get(API + "reports/performance/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_zero_data_business(self):
        data = self.report()
        self.assertEqual(data["total_sales"], "0.00")
        self.assertEqual(data["total_expenses"], "0.00")
        self.assertEqual(data["profit"], "0.00")
        self.assertEqual(data["outstanding_receivables"], "0.00")
        self.assertEqual(data["outstanding_payables"], "0.00")
        self.assertEqual(data["low_stock_count"], 0)

    def test_default_range_is_current_month(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 1, 0, 0, 0))     # in month
        self.make_sale_at(self.user_a, "20.00", utc(2026, 9, 30, 23, 59, 59))  # in month
        self.make_sale_at(self.user_a, "999.00", utc(2026, 8, 31, 23, 59, 59))  # previous month
        data = self.report()
        self.assertEqual(data["total_sales"], "30.00")

    def test_explicit_date_range(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 10))
        self.make_sale_at(self.user_a, "20.00", utc(2026, 9, 20))
        data = self.report("?from=2026-09-15&to=2026-09-25")
        self.assertEqual(data["total_sales"], "20.00")

    def test_sales_and_expense_aggregation_and_profit(self):
        self.make_sale_at(self.user_a, "100.00", utc(2026, 9, 10))
        self.make_expense(self.user_a, "40.00", date(2026, 9, 10))
        data = self.report("?from=2026-09-01&to=2026-09-30")
        self.assertEqual(data["total_sales"], "100.00")
        self.assertEqual(data["total_expenses"], "40.00")
        self.assertEqual(data["profit"], "60.00")

    def test_profit_can_be_negative(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 10))
        self.make_expense(self.user_a, "25.00", date(2026, 9, 10))
        data = self.report("?from=2026-09-01&to=2026-09-30")
        self.assertEqual(data["profit"], "-15.00")

    def test_outstanding_receivables_from_unpaid_and_partial_sales_only(self):
        product = self.make_product(selling_price="10.00", initial_quantity=100)
        self.make_sale(product["id"], quantity=2, paid="20.00")  # fully paid: 0 remaining
        self.make_sale(product["id"], quantity=3, paid="10.00")  # PARTIAL: remaining 20
        self.make_sale(product["id"], quantity=1)  # UNPAID: remaining 10
        data = self.report("?from=2026-01-01&to=2026-12-31")
        self.assertEqual(data["outstanding_receivables"], "30.00")

    def test_outstanding_payables_only_counts_payable_debts(self):
        self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "Supplier A", "original_amount": "100.00"},
            format="json",
        )
        payable_2 = self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "Supplier B", "original_amount": "50.00"},
            format="json",
        ).json()
        self.client_a.post(
            API + f"debts/{payable_2['id']}/payments/", {"amount": "20.00"}, format="json"
        )
        # A RECEIVABLE debt must never be added to outstanding_payables, and
        # must not double-count into outstanding_receivables either (that
        # stays sourced from Sale/Payment only).
        self.client_a.post(
            API + "debts/",
            {"debt_type": "RECEIVABLE", "party_name": "Some customer", "original_amount": "999.00"},
            format="json",
        )
        data = self.report()
        self.assertEqual(data["outstanding_payables"], "130.00")
        self.assertEqual(data["outstanding_receivables"], "0.00")

    def test_low_stock_count(self):
        self.make_product(name="Low", initial_quantity=1, minimum_stock=5)
        self.make_product(name="Also low", initial_quantity=0, minimum_stock=0)
        self.make_product(name="Fine", initial_quantity=50, minimum_stock=5)
        data = self.report()
        self.assertEqual(data["low_stock_count"], 2)

    def test_cross_user_isolation(self):
        self.make_sale_at(self.user_b, "999.00", utc(2026, 9, 10))
        self.make_expense(self.user_b, "111.00", date(2026, 9, 10))
        self.client_a.post(
            API + "debts/",
            {"debt_type": "PAYABLE", "party_name": "X", "original_amount": "1.00"},
            format="json",
        )
        data_a = self.report()
        self.assertEqual(data_a["total_sales"], "0.00")
        self.assertEqual(data_a["total_expenses"], "0.00")
        self.assertEqual(data_a["outstanding_payables"], "1.00")
        data_b = self.report(client=self.client_b)
        self.assertEqual(data_b["outstanding_payables"], "0.00")

    def test_invalid_date_input_returns_400(self):
        with PATCH_TODAY:
            response = self.client_a.get(API + "reports/performance/?from=not-a-date")
        self.assertEqual(response.status_code, 400)
        self.assertIn("from", response.json())

    def test_from_after_to_returns_400(self):
        with PATCH_TODAY:
            response = self.client_a.get(
                API + "reports/performance/?from=2026-09-20&to=2026-09-01"
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("to", response.json())

    def test_decimal_precision_is_exact(self):
        product = self.make_product(selling_price="0.10", initial_quantity=100)
        for _ in range(3):
            self.make_sale(product["id"], quantity=1)
        data = self.report("?from=2026-01-01&to=2026-12-31")
        self.assertEqual(data["total_sales"], "0.30")

    def test_unauthenticated_user_gets_401(self):
        response = APIClient().get(API + "reports/performance/")
        self.assertEqual(response.status_code, 401)


class DashboardSeriesTests(BusinessAPITestCase):
    def series(self, query="", client=None):
        with PATCH_TODAY:
            response = (client or self.client_a).get(API + "dashboard/series/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["series"]

    def test_default_period_is_day_with_seven_trailing_points(self):
        points = self.series()
        self.assertEqual(len(points), 7)
        self.assertEqual(points[0]["period"], "2026-09-18")
        self.assertEqual(points[-1]["period"], "2026-09-24")

    def test_day_points_aggregate_their_own_day_only(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 20))
        self.make_sale_at(self.user_a, "5.00", utc(2026, 9, 21))
        self.make_expense(self.user_a, "2.00", date(2026, 9, 20))
        points = {p["period"]: p for p in self.series("?period=day&from=2026-09-20&to=2026-09-21")}
        self.assertEqual(points["2026-09-20"]["sales"], "10.00")
        self.assertEqual(points["2026-09-20"]["expenses"], "2.00")
        self.assertEqual(points["2026-09-20"]["profit"], "8.00")
        self.assertEqual(points["2026-09-21"]["sales"], "5.00")

    def test_week_points_are_monday_to_sunday(self):
        # Mon 14 Sep - Sun 20 Sep is one full week; Mon 21 Sep starts the next.
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 14, 0, 0, 0))
        self.make_sale_at(self.user_a, "20.00", utc(2026, 9, 20, 23, 59, 59))
        self.make_sale_at(self.user_a, "30.00", utc(2026, 9, 21, 0, 0, 0))
        points = self.series("?period=week&from=2026-09-14&to=2026-09-21")
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["period"], "2026-09-14")
        self.assertEqual(points[0]["sales"], "30.00")
        self.assertEqual(points[1]["period"], "2026-09-21")
        self.assertEqual(points[1]["sales"], "30.00")

    def test_month_points_are_calendar_months(self):
        self.make_sale_at(self.user_a, "5.00", utc(2026, 9, 1, 0, 0, 0))
        self.make_sale_at(self.user_a, "9.00", utc(2026, 9, 30, 23, 59, 59))
        self.make_sale_at(self.user_a, "1000.00", utc(2026, 10, 1, 0, 0, 0))
        points = self.series("?period=month&from=2026-09-01&to=2026-10-01")
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["period"], "2026-09-01")
        self.assertEqual(points[0]["sales"], "14.00")
        self.assertEqual(points[1]["period"], "2026-10-01")
        self.assertEqual(points[1]["sales"], "1000.00")

    def test_invalid_period_returns_400(self):
        with PATCH_TODAY:
            response = self.client_a.get(API + "dashboard/series/?period=year")
        self.assertEqual(response.status_code, 400)
        self.assertIn("period", response.json())

    def test_range_too_large_for_period_returns_400(self):
        with PATCH_TODAY:
            response = self.client_a.get(
                API + "dashboard/series/?period=day&from=2000-01-01&to=2026-09-24"
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("to", response.json())

    def test_from_after_to_returns_400(self):
        with PATCH_TODAY:
            response = self.client_a.get(
                API + "dashboard/series/?from=2026-09-20&to=2026-09-01"
            )
        self.assertEqual(response.status_code, 400)

    def test_cross_user_isolation(self):
        self.make_sale_at(self.user_b, "999.00", utc(2026, 9, 20))
        points = {
            p["period"]: p
            for p in self.series("?period=day&from=2026-09-20&to=2026-09-20")
        }
        self.assertEqual(points["2026-09-20"]["sales"], "0.00")

    def test_unauthenticated_user_gets_401(self):
        response = APIClient().get(API + "dashboard/series/")
        self.assertEqual(response.status_code, 401)
