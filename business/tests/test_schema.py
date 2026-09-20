from rest_framework.test import APITestCase


class OpenAPISchemaTests(APITestCase):
    """The published OpenAPI schema must describe the final API behaviour."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = cls.client_class().get("/api/schema/?format=json").json()

    def query_params(self, path, method="get"):
        operation = self.schema["paths"][path][method]
        return {p["name"] for p in operation.get("parameters", []) if p["in"] == "query"}

    def test_sales_list_documents_filters_ordering_and_pagination(self):
        params = self.query_params("/api/business/sales/")
        self.assertTrue({"date_from", "date_to", "ordering", "page", "page_size"} <= params)

    def test_expenses_list_documents_filters_ordering_and_pagination(self):
        params = self.query_params("/api/business/expenses/")
        self.assertTrue({"category", "date_from", "date_to", "ordering", "page", "page_size"} <= params)

    def test_products_and_customers_document_search_and_ordering(self):
        for path in ("/api/business/products/", "/api/business/customers/"):
            params = self.query_params(path)
            self.assertTrue({"search", "ordering"} <= params, path)
            self.assertFalse({"page", "page_size"} & params, path)

    def test_sale_update_does_not_expose_paid_amount(self):
        properties = self.schema["components"]["schemas"]["SaleUpdate"]["properties"]
        self.assertEqual(set(properties), {"customer", "items"})

    def test_dashboard_and_customer_history_are_documented(self):
        schemas = self.schema["components"]["schemas"]
        self.assertTrue({"today", "week", "month"} <= set(schemas["Dashboard"]["properties"]))
        self.assertEqual(
            set(schemas["CustomerHistory"]["properties"]), {"customer", "summary", "sales"}
        )
        self.assertEqual(
            set(schemas["CustomerSummary"]["properties"]),
            {"total_purchases", "total_paid", "outstanding_balance"},
        )
