from decimal import Decimal

from django.db import transaction

from business.models import Payment, Sale


@transaction.atomic
def add_payment(
    *,
    sale_id,
    business,
    amount,
    payment_method,
    note="",
):
    sale = Sale.objects.select_for_update().filter(
        id=sale_id,
        business=business,
    ).first()

    if sale is None:
        raise ValueError("Sale not found.")

    amount = Decimal(amount)

    remaining = sale.total_amount - sale.paid_amount

    if amount <= 0:
        raise ValueError("Payment must be greater than zero.")

    if amount > remaining:
        raise ValueError(
            "Payment cannot exceed remaining amount."
        )

    payment = Payment.objects.create(
        sale=sale,
        amount=amount,
        payment_method=payment_method,
        note=note,
    )

    sale.paid_amount += amount

    if sale.paid_amount == sale.total_amount:
        sale.payment_status = Sale.PaymentStatus.PAID
    elif sale.paid_amount > 0:
        sale.payment_status = Sale.PaymentStatus.PARTIAL
    else:
        sale.payment_status = Sale.PaymentStatus.UNPAID

    sale.save(
        update_fields=[
            "paid_amount",
            "payment_status",
        ]
    )

    return payment