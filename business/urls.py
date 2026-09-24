from django.urls import path
from business.views import (
    BusinessView,
    CategoryDetailView,
    CategoryListCreateView,
    CustomerDetailView,
    CustomerHistoryView,
    CustomerListCreateView,
    DashboardSeriesView,
    DashboardView,
    DebtDetailView,
    DebtDueListView,
    DebtListCreateView,
    DebtPaymentCreateView,
    ExpenseDetailView,
    ExpenseListCreateView,
    InvoiceCancelView,
    InvoiceCreateView,
    InvoiceDetailView,
    InvoiceListView,
    InvoicePdfView,
    LowStockProductListView,
    OutOfStockProductListView,
    PaymentCreateView,
    PerformanceReportView,
    ProductDetailView,
    ProductListCreateView,
    ProductStockAdjustView,
    SaleDetailView,
    SaleListCreateView,
)


urlpatterns = [
    path(
        "",
        BusinessView.as_view(),
        name="business",
    ),

    path(
        "dashboard/",
        DashboardView.as_view(),
        name="dashboard",
    ),

    path(
        "dashboard/series/",
        DashboardSeriesView.as_view(),
        name="dashboard-series",
    ),

    path(
        "reports/performance/",
        PerformanceReportView.as_view(),
        name="reports-performance",
    ),

    path(
        "categories/",
        CategoryListCreateView.as_view(),
        name="category-list-create",
    ),

    path(
        "categories/<int:pk>/",
        CategoryDetailView.as_view(),
        name="category-detail",
    ),

    path(
        "products/", 
         ProductListCreateView.as_view(),
        name="product-list-create"
        ),

    path(
        "products/low-stock/",
          LowStockProductListView.as_view(),
         name="product-low-stock"
        ),
    path(
        "products/out-of-stock/", 
        OutOfStockProductListView.as_view(),
        name="product-out-of-stock"
        ),
    path(
        "products/<int:pk>/",
          ProductDetailView.as_view(),
         name="product-detail"
         ),
    path(
        "products/<int:pk>/adjust-stock/",
          ProductStockAdjustView.as_view(),
         name="product-adjust-stock"
         ),
    path(
        "customers/",
        CustomerListCreateView.as_view(),
        name="customer-list-create",
    ),

    path(
        "customers/<int:pk>/",
        CustomerDetailView.as_view(),
        name="customer-detail",
    ),

    path(
        "customers/<int:pk>/history/",
        CustomerHistoryView.as_view(),
        name="customer-history",
    ),

    path(
        "sales/",
        SaleListCreateView.as_view(),
        name="sale-list-create",
    ),

    path(
        "sales/<int:pk>/",
        SaleDetailView.as_view(),
        name="sale-detail",
    ),

    path(
        "sales/<int:sale_id>/payments/",
        PaymentCreateView.as_view(),
        name="sale-payment-create",
    ),

    path(
        "sales/<int:sale_id>/invoice/",
        InvoiceCreateView.as_view(),
        name="sale-invoice-create",
    ),

    path(
        "invoices/",
        InvoiceListView.as_view(),
        name="invoice-list",
    ),

    path(
        "invoices/<int:pk>/",
        InvoiceDetailView.as_view(),
        name="invoice-detail",
    ),

    path(
        "invoices/<int:pk>/cancel/",
        InvoiceCancelView.as_view(),
        name="invoice-cancel",
    ),

    path(
        "invoices/<int:pk>/pdf/",
        InvoicePdfView.as_view(),
        name="invoice-pdf",
    ),

    path(
        "debts/",
        DebtListCreateView.as_view(),
        name="debt-list-create",
    ),

    path(
        "debts/due/",
        DebtDueListView.as_view(),
        name="debt-due-list",
    ),

    path(
        "debts/<int:pk>/",
        DebtDetailView.as_view(),
        name="debt-detail",
    ),

    path(
        "debts/<int:debt_id>/payments/",
        DebtPaymentCreateView.as_view(),
        name="debt-payment-create",
    ),

    path(
        "expenses/",
        ExpenseListCreateView.as_view(),
        name="expense-list-create",
    ),

    path(
        "expenses/<int:pk>/",
        ExpenseDetailView.as_view(),
        name="expense-detail",
    ),
]