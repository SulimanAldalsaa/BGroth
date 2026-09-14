from django.urls import path

from business.views import (

    BusinessView,
    ProductListCreateView,
    ProductDetailView,
    CustomerListCreateView,
    CustomerDetailView,
    SaleListCreateView,
    ExpenseListCreateView,
    ExpenseDetailView,
)


urlpatterns = [
    path(
        "business/",
        BusinessView.as_view(),
        name="business",
    ),

    path(
        "products/",
        ProductListCreateView.as_view(),
        name="product-list-create",
    ),

    path(
        "products/<int:pk>/",
        ProductDetailView.as_view(),
        name="product-detail",
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
        "sales/",
        SaleListCreateView.as_view(),
        name="sale-list-create",
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