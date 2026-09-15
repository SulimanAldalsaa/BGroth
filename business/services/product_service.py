from django.db import transaction

from business.models import Product, StockMovement


@transaction.atomic
def create_product(
    *,
    business,
    user,
    validated_data,
):
    initial_quantity = validated_data.pop(
        "initial_quantity",
        0,
    )

    product = Product.objects.create(
        business=business,
        quantity=initial_quantity,
        **validated_data,
    )

    if initial_quantity > 0:
        StockMovement.objects.create(
            product=product,
            movement_type=StockMovement.MovementType.IN,
            quantity=initial_quantity,
            previous_quantity=0,
            new_quantity=initial_quantity,
            reason="Initial stock",
            created_by=user,
        )

    return product