from business.models import Sale


def get_business_sales(business):
    return (
        Sale.objects
        .filter(business=business)
        .prefetch_related("items__product")
        .select_related("customer")
        .order_by("-created_at")
    )


def get_business_sale(business, sale_id):
    return (
        Sale.objects
        .filter(
            business=business,
            id=sale_id,
        )
        .prefetch_related("items__product")
        .select_related("customer")
        .first()
    )