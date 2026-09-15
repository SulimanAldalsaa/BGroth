from django.db import transaction

from business.models import Product, StockMovement


@transaction.atomic
def adjust_stock(
    *,
    product_id,
    business,
    user,
    quantity,
    movement_type,
    reason="",
):
    product = Product.objects.select_for_update().get(
        id=product_id,
        business=business,
    )

    previous_quantity = product.quantity

    if movement_type == StockMovement.MovementType.IN:
        new_quantity = previous_quantity + quantity

    elif movement_type == StockMovement.MovementType.OUT:
        if quantity > previous_quantity:
            raise ValueError("Insufficient stock.")

        new_quantity = previous_quantity - quantity

    elif movement_type == StockMovement.MovementType.ADJUSTMENT:
        new_quantity = quantity

    else:
        raise ValueError("Invalid stock movement type.")

    product.quantity = new_quantity
    product.save(update_fields=["quantity", "updated_at"])

    StockMovement.objects.create(
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        reason=reason,
        created_by=user,
    )

    return product