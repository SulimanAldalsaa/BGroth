from django.db import models


class DebtPayment(models.Model):
    """A single payment against a Debt (BR-9: transaction history is never lost).

    ``on_delete=PROTECT`` means a Debt that has any recorded payment cannot be
    deleted at all, satisfying BR-9 without needing a bespoke confirmation flow.
    """

    debt = models.ForeignKey(
        "business.Debt",
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} - Debt #{self.debt_id}"
