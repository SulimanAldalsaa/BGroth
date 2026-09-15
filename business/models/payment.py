from django.db import models


class Payment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        OTHER = "OTHER", "Other"

    sale = models.ForeignKey(
        "business.Sale",
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    note = models.CharField(max_length=255, blank=True)

    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} - Sale #{self.sale_id}"