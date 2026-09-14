from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="products",
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    selling_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    quantity = models.PositiveIntegerField(default=0)

    minimum_stock = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name