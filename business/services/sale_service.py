from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from business.models import Customer, Product, Sale, SaleItem


class SaleService:

    @staticmethod
    @transaction.atomic
    def create_sale(
        *,
        business,
        customer_id,
        paid_amount,
        items,
    ):
        customer = None

        if customer_id is not None:
            customer = Customer.objects.filter(
                id=customer_id,
                business=business,
            ).first()

            if customer is None:
                raise ValidationError(
                    {
                        "customer": "Customer does not exist."
                    }
                )

        if not items:
            raise ValidationError(
                {
                    "items": "At least one product is required."
                }
            )

        product_ids = [
            item["product"]
            for item in items
        ]

        if len(product_ids) != len(set(product_ids)):
            raise ValidationError(
                {
                    "items": (
                        "A product cannot appear more than once."
                    )
                }
            )

        products = (
            Product.objects
            .select_for_update()
            .filter(
                business=business,
                id__in=product_ids,
            )
        )

        products_by_id = {
            product.id: product
            for product in products
        }

        if len(products_by_id) != len(product_ids):
            raise ValidationError(
                {
                    "items": (
                        "One or more products do not exist."
                    )
                }
            )

        total_amount = Decimal("0.00")
        sale_items = []

        for item in items:
            product = products_by_id[item["product"]]
            quantity = item["quantity"]

            if quantity > product.quantity:
                raise ValidationError(
                    {
                        "items": (
                            f"Not enough stock for "
                            f"'{product.name}'."
                        )
                    }
                )

            unit_price = product.selling_price

            subtotal = unit_price * quantity

            total_amount += subtotal

            sale_items.append(
                {
                    "product": product,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

        if paid_amount > total_amount:
            raise ValidationError(
                {
                    "paid_amount": (
                        "Paid amount cannot exceed "
                        "total amount."
                    )
                }
            )

        sale = Sale.objects.create(
            business=business,
            customer=customer,
            total_amount=total_amount,
            paid_amount=paid_amount,
        )

        for item in sale_items:
            product = item["product"]
            quantity = item["quantity"]

            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=item["unit_price"],
                subtotal=item["subtotal"],
            )

            product.quantity -= quantity
            product.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ]
            )

        return sale