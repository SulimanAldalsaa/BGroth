from django.db import models

from business.models import Product


def get_business_products(business):
    return Product.objects.filter(
        business=business
    ).select_related("category")


def get_low_stock_products(business):
    return Product.objects.filter(
        business=business,
        quantity__lte=models.F("minimum_stock"),
    )


def get_out_of_stock_products(business):
    return Product.objects.filter(
        business=business,
        quantity=0,
    )