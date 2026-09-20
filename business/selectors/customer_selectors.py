from decimal import Decimal

from django.db.models import Sum

from business.models import Sale


def get_customer_sales(customer):
    return (
        Sale.objects.filter(
            business_id=customer.business_id,
            customer=customer,
        )
        .prefetch_related("items")
        .order_by("-sold_at", "-id")
    )


def get_customer_summary(customer):
    """Totals calculated from the customer's sales; nothing is stored twice."""
    totals = Sale.objects.filter(
        business_id=customer.business_id,
        customer=customer,
    ).aggregate(
        total_purchases=Sum("total_amount"),
        total_paid=Sum("paid_amount"),
    )

    total_purchases = totals["total_purchases"] or Decimal("0")
    total_paid = totals["total_paid"] or Decimal("0")

    return {
        "total_purchases": total_purchases,
        "total_paid": total_paid,
        "outstanding_balance": total_purchases - total_paid,
    }
