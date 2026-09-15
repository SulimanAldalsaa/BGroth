from django.db import models


class Expense(models.Model):
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="expenses",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    category = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    expense_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.amount}"