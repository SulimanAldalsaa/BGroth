from datetime import date

from .base import API, BusinessAPITestCase


class ExpenseListQueryTests(BusinessAPITestCase):
    def setUp(self):
        super().setUp()
        self.early = self.make_expense(self.user_a, "10.00", date(2026, 9, 1), category="rent")
        self.middle = self.make_expense(self.user_a, "30.00", date(2026, 9, 10), category="tax")
        self.late = self.make_expense(self.user_a, "20.00", date(2026, 9, 20), category="rent")

    def ids(self, query="", client=None):
        response = (client or self.client_a).get(API + "expenses/" + query)
        self.assertEqual(response.status_code, 200, response.content)
        return [expense["id"] for expense in response.json()]

    def test_default_order_is_newest_date_first(self):
        self.assertEqual(self.ids(), [self.late.id, self.middle.id, self.early.id])

    def test_date_from(self):
        self.assertEqual(self.ids("?date_from=2026-09-10"), [self.late.id, self.middle.id])

    def test_date_to(self):
        self.assertEqual(self.ids("?date_to=2026-09-10"), [self.middle.id, self.early.id])

    def test_date_from_and_date_to(self):
        self.assertEqual(self.ids("?date_from=2026-09-05&date_to=2026-09-15"), [self.middle.id])
        self.assertEqual(self.ids("?date_from=2026-09-01&date_to=2026-09-20"), [self.late.id, self.middle.id, self.early.id])

    def test_range_includes_both_end_dates(self):
        self.assertEqual(self.ids("?date_from=2026-09-10&date_to=2026-09-10"), [self.middle.id])
        self.assertEqual(self.ids("?date_from=2026-09-20"), [self.late.id])
        self.assertEqual(self.ids("?date_to=2026-09-01"), [self.early.id])

    def test_no_match_returns_empty_list(self):
        self.assertEqual(self.ids("?date_from=2027-01-01"), [])

    def test_blank_date_parameters_are_ignored(self):
        self.assertEqual(self.ids("?date_from=&date_to="), [self.late.id, self.middle.id, self.early.id])

    def test_invalid_dates_return_400_naming_the_parameter(self):
        for query, field in (
            ("?date_from=yesterday", "date_from"),
            ("?date_to=2026-02-30", "date_to"),
            ("?date_from=10/09/2026", "date_from"),
            ("?date_from=2026-09-20&date_to=2026-09-01", "date_to"),
        ):
            response = self.client_a.get(API + "expenses/" + query)
            self.assertEqual(response.status_code, 400, query)
            self.assertIn(field, response.json(), query)

    def test_category_filter_still_works_and_combines_with_dates(self):
        self.assertEqual(self.ids("?category=rent"), [self.late.id, self.early.id])
        self.assertEqual(self.ids("?category=rent&date_from=2026-09-10"), [self.late.id])
        self.assertEqual(self.ids("?category=tax&date_to=2026-09-05"), [])

    def test_filtering_never_returns_another_business(self):
        other = self.make_expense(self.user_b, "99.00", date(2026, 9, 10), category="rent")
        self.assertNotIn(other.id, self.ids("?date_from=2026-09-01&date_to=2026-09-30&category=rent"))
        self.assertEqual(self.ids("?date_from=2026-09-01&category=rent", client=self.client_b), [other.id])

    def test_ordering(self):
        self.assertEqual(self.ids("?ordering=amount"), [self.early.id, self.late.id, self.middle.id])
        self.assertEqual(self.ids("?ordering=-amount"), [self.middle.id, self.late.id, self.early.id])
        self.assertEqual(self.ids("?ordering=expense_date"), [self.early.id, self.middle.id, self.late.id])

    def test_ordering_combines_with_filters(self):
        self.assertEqual(self.ids("?category=rent&ordering=amount"), [self.early.id, self.late.id])
        self.assertEqual(self.ids("?date_from=2026-09-10&ordering=amount"), [self.late.id, self.middle.id])

    def test_without_page_parameters_the_response_is_a_plain_array(self):
        self.assertIsInstance(self.client_a.get(API + "expenses/").json(), list)

    def test_pagination(self):
        first = self.client_a.get(API + "expenses/?page_size=2").json()
        self.assertEqual(first["count"], 3)
        self.assertIsNotNone(first["next"])
        self.assertEqual([e["id"] for e in first["results"]], [self.late.id, self.middle.id])
        second = self.client_a.get(API + "expenses/?page=2&page_size=2").json()
        self.assertEqual([e["id"] for e in second["results"]], [self.early.id])
        self.assertIsNone(second["next"])

    def test_pagination_keeps_filters_and_ordering(self):
        body = self.client_a.get(API + "expenses/?category=rent&ordering=amount&page_size=1").json()
        self.assertEqual(body["count"], 2)
        self.assertEqual([e["id"] for e in body["results"]], [self.early.id])

    def test_pages_do_not_overlap_when_values_tie(self):
        for _ in range(4):
            self.make_expense(self.user_a, "5.00", date(2026, 9, 5))
        seen = []
        for page in range(1, 4):
            body = self.client_a.get(API + f"expenses/?ordering=amount&page={page}&page_size=3").json()
            seen += [e["id"] for e in body["results"]]
        self.assertEqual(len(seen), 7)
        self.assertEqual(len(set(seen)), 7)

    def test_pagination_only_counts_own_expenses(self):
        self.make_expense(self.user_b, "1.00", date(2026, 9, 10))
        self.assertEqual(self.client_a.get(API + "expenses/?page_size=1").json()["count"], 3)

    def test_invalid_date_is_rejected_when_paginating_too(self):
        self.assertEqual(self.client_a.get(API + "expenses/?date_from=oops&page_size=2").status_code, 400)
