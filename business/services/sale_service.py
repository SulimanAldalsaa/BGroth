from decimal import Decimal

from django.db import transaction

from business.models import (
    Customer,
    Payment,
    Product,
    Sale,
    SaleItem,
    StockMovement,
)


@transaction.atomic
def create_sale(
    *,
    business,
    user,
    customer_id,
    paid_amount,
    items,
):
    customer = None

    if customer_id:
        customer = Customer.objects.filter(
            id=customer_id,
            business=business,
        ).first()

        if customer is None:
            raise ValueError("Invalid customer.")

    total_amount = Decimal("0")
    prepared_items = []

    for item in items:
        product = Product.objects.select_for_update().filter(
            id=item["product"],
            business=business,
        ).first()

        if product is None:
            raise ValueError("Invalid product.")

        quantity = item["quantity"]

        if quantity > product.quantity:
            raise ValueError(
                f"Insufficient stock for {product.name}."
            )

        unit_price = product.selling_price
        subtotal = unit_price * quantity

        total_amount += subtotal

        prepared_items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )

    paid_amount = Decimal(paid_amount)

    if paid_amount > total_amount:
        raise ValueError(
            "Paid amount cannot exceed total amount."
        )

    if paid_amount == total_amount:
        payment_status = Sale.PaymentStatus.PAID
    elif paid_amount > 0:
        payment_status = Sale.PaymentStatus.PARTIAL
    else:
        payment_status = Sale.PaymentStatus.UNPAID

    sale = Sale.objects.create(
        business=business,
        customer=customer,
        total_amount=total_amount,
        paid_amount=paid_amount,
        payment_status=payment_status,
    )

    if paid_amount > 0:
        Payment.objects.create(
            sale=sale,
            amount=paid_amount,
            payment_method=Payment.PaymentMethod.CASH,
        )

    for item in prepared_items:
        product = item["product"]

        previous_quantity = product.quantity
        new_quantity = previous_quantity - item["quantity"]

        SaleItem.objects.create(
            sale=sale,
            product=product,
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            subtotal=item["subtotal"],
        )

        product.quantity = new_quantity
        product.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        StockMovement.objects.create(
            product=product,
            movement_type=StockMovement.MovementType.SALE,
            quantity=item["quantity"],
            previous_quantity=previous_quantity,
            new_quantity=new_quantity,
            reason=f"Sale #{sale.id}",
            created_by=user,
        )

    return sale