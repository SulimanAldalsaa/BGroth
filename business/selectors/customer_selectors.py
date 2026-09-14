from business.models import Customer


def get_business_customers(business):
    return Customer.objects.filter(
        business=business
    ).order_by("-created_at")


def get_business_customer(business, customer_id):
    return Customer.objects.filter(
        business=business,
        id=customer_id,
    ).first()