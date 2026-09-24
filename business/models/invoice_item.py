from django.db import models


class InvoiceItem(models.Model):
    """Historical snapshot of a sold line item at the moment the invoice was issued.

    Deliberately stores ``product_name``/``unit_price`` as plain values instead of
    a ``Product`` FK: later renames or price changes on the product must never
    change an already-issued invoice (BR-12).
    """

    invoice = models.ForeignKey(
        "business.Invoice",
        on_delete=models.CASCADE,
        related_name="items",
    )

    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"
