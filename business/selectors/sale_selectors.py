from business.models import Sale


def get_business_sales(business):
    return Sale.objects.filter(
        business=business
    ).prefetch_related("items")