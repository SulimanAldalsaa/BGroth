from datetime import date
from unittest.mock import patch

from .base import API, BusinessAPITestCase, utc

# Wednesday 16 Sep 2026: the week is Mon 14 - Sun 20 Sep, the month is 1 - 30 Sep.
TODAY = date(2026, 9, 16)
PATCH_TODAY = patch("business.selectors.dashboard_selectors.timezone.localdate", return_value=TODAY)

ZERO = {"sales": "0.00", "expenses": "0.00", "profit": "0.00"}


class DashboardTests(BusinessAPITestCase):
    def dashboard(self, client=None):
        with PATCH_TODAY:
            response = (client or self.client_a).get(API + "dashboard/")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_zero_data(self):
        data = self.dashboard()
        self.assertEqual(data["today"], ZERO)
        self.assertEqual(data["week"], ZERO)
        self.assertEqual(data["month"], ZERO)

    def test_today(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 16, 0, 0, 0))
        self.make_sale_at(self.user_a, "5.50", utc(2026, 9, 16, 23, 59, 59))
        self.make_expense(self.user_a, "3.00", date(2026, 9, 16))
        self.make_sale_at(self.user_a, "100.00", utc(2026, 9, 15))
        self.make_expense(self.user_a, "50.00", date(2026, 9, 17))
        self.assertEqual(
            self.dashboard()["today"], {"sales": "15.50", "expenses": "3.00", "profit": "12.50"}
        )

    def test_current_week_runs_monday_to_sunday(self):
        for sold_at, amount in (
            (utc(2026, 9, 16), "10.00"),          # today
            (utc(2026, 9, 14, 0, 0, 0), "20.00"),  # Monday, first moment of the week
            (utc(2026, 9, 20, 23, 59, 59), "80.00"),  # Sunday, last moment of the week
            (utc(2026, 9, 13, 23, 59, 59), "40.00"),  # previous Sunday: not in the week
            (utc(2026, 9, 21, 0, 0, 0), "1000.00"),   # next Monday: not in the week
        ):
            self.make_sale_at(self.user_a, amount, sold_at)
        for expense_date, amount in (
            (date(2026, 9, 16), "3.00"),
            (date(2026, 9, 14), "4.00"),
            (date(2026, 9, 13), "500.00"),
            (date(2026, 9, 21), "600.00"),
        ):
            self.make_expense(self.user_a, amount, expense_date)
        self.assertEqual(
            self.dashboard()["week"], {"sales": "110.00", "expenses": "7.00", "profit": "103.00"}
        )

    def test_current_month_boundaries(self):
        for sold_at, amount in (
            (utc(2026, 9, 1, 0, 0, 0), "5.00"),        # first moment of the month
            (utc(2026, 9, 16), "10.00"),
            (utc(2026, 9, 30, 23, 59, 59), "20.00"),   # last moment of the month
            (utc(2026, 9, 13), "40.00"),               # previous week, same month
            (utc(2026, 8, 31, 23, 59, 59), "1000.00"),  # previous month
            (utc(2026, 10, 1, 0, 0, 0), "2000.00"),     # next month
        ):
            self.make_sale_at(self.user_a, amount, sold_at)
        for expense_date, amount in (
            (date(2026, 9, 1), "6.00"),
            (date(2026, 9, 30), "9.00"),
            (date(2026, 8, 31), "700.00"),
            (date(2026, 10, 1), "800.00"),
        ):
            self.make_expense(self.user_a, amount, expense_date)
        self.assertEqual(
            self.dashboard()["month"], {"sales": "75.00", "expenses": "15.00", "profit": "60.00"}
        )

    def test_profit_can_be_negative(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 16))
        self.make_expense(self.user_a, "25.00", date(2026, 9, 16))
        self.assertEqual(
            self.dashboard()["today"], {"sales": "10.00", "expenses": "25.00", "profit": "-15.00"}
        )

    def test_periods_are_reported_together(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 16))
        self.make_sale_at(self.user_a, "20.00", utc(2026, 9, 14))
        self.make_sale_at(self.user_a, "40.00", utc(2026, 9, 2))
        data = self.dashboard()
        self.assertEqual(data["today"]["sales"], "10.00")
        self.assertEqual(data["week"]["sales"], "30.00")
        self.assertEqual(data["month"]["sales"], "70.00")

    def test_month_end_is_correct_for_february(self):
        with patch(
            "business.selectors.dashboard_selectors.timezone.localdate",
            return_value=date(2028, 2, 10),  # leap year
        ):
            self.make_sale_at(self.user_a, "7.00", utc(2028, 2, 29))
            self.make_sale_at(self.user_a, "9.00", utc(2028, 3, 1))
            month = self.client_a.get(API + "dashboard/").json()["month"]
        self.assertEqual(month["sales"], "7.00")

    def test_flat_today_fields_are_kept_for_existing_clients(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 16))
        self.make_expense(self.user_a, "3.00", date(2026, 9, 16))
        data = self.dashboard()
        self.assertEqual(data["sales_today"], "10.00")
        self.assertEqual(data["expenses_today"], "3.00")
        self.assertEqual(data["profit_today"], "7.00")

    def test_sales_recorded_through_the_api_appear_today(self):
        product = self.make_product()
        self.make_sale(product["id"], quantity=4)
        data = self.client_a.get(API + "dashboard/").json()
        self.assertEqual(data["today"]["sales"], "10.00")
        self.assertEqual(data["week"]["sales"], "10.00")
        self.assertEqual(data["month"]["sales"], "10.00")

    def test_businesses_are_isolated(self):
        self.make_sale_at(self.user_b, "999.00", utc(2026, 9, 16))
        self.make_expense(self.user_b, "111.00", date(2026, 9, 16))
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 16))
        a = self.dashboard(self.client_a)
        b = self.dashboard(self.client_b)
        self.assertEqual(a["month"], {"sales": "10.00", "expenses": "0.00", "profit": "10.00"})
        self.assertEqual(b["month"], {"sales": "999.00", "expenses": "111.00", "profit": "888.00"})
        self.assertEqual(b["today"]["profit"], "888.00")

    def test_business_without_data_is_not_affected_by_others(self):
        self.make_sale_at(self.user_a, "10.00", utc(2026, 9, 16))
        self.assertEqual(self.dashboard(self.client_b)["month"], ZERO)
