from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Sale(models.Model):
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="sales",
    )

    customer = models.ForeignKey(
        "business.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale #{self.id}"

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "business.Product",
        on_delete=models.PROTECT,
        related_name="sale_items",
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"