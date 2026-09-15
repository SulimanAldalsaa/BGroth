from django.urls import path
from business.views import (
    BusinessView,
    CategoryDetailView,
    CategoryListCreateView,
    CustomerDetailView,
    CustomerHistoryView,
    CustomerListCreateView,
    DashboardView,
    ExpenseDetailView,
    ExpenseListCreateView,
    LowStockProductListView,
    OutOfStockProductListView,
    PaymentCreateView,
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