from business.models import Product


def get_business_products(business):
    return Product.objects.filter(
        business=business
    ).order_by("-created_at")


def get_business_product(business, product_id):
    return Product.objects.filter(
        business=business,
        id=product_id,
    ).first()