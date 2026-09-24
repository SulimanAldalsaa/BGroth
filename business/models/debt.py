from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class Debt(models.Model):

    class DebtType(models.TextChoices):
        RECEIVABLE = "RECEIVABLE", "Receivable"
        PAYABLE = "PAYABLE", "Payable"

    class Status(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PARTIAL = "PARTIAL", "Partial"
        PAID = "PAID", "Paid"

    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="debts",
    )

    # BR-8: mandatory, no default.
    debt_type = models.CharField(
        max_length=20,
        choices=DebtType.choices,
    )

    party_name = models.CharField(max_length=255)

    # Optional links: a RECEIVABLE may reference the customer/sale it came
    # from; a PAYABLE (e.g. a supplier) usually has neither.
    customer = models.ForeignKey(
        "business.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debts",
    )
    sale = models.ForeignKey(
        "business.Sale",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debts",
    )

    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    due_date = models.DateField(null=True, blank=True)

    # BR-10: derived by recalculate_status(), never trusted from the client.
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID,
    )

    notes = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(paid_amount__gte=0),
                name="debt_paid_amount_gte_0",
            ),
            models.CheckConstraint(
                condition=Q(paid_amount__lte=F("original_amount")),
                name="debt_paid_amount_lte_original_amount",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "due_date"]),
            models.Index(fields=["business", "status"]),
        ]

    @property
    def remaining_amount(self):
        return self.original_amount - self.paid_amount

    def recalculate_status(self):
        """BR-10: PAID only when paid_amount == original_amount."""
        if self.paid_amount <= 0:
            self.status = self.Status.UNPAID
        elif self.paid_amount < self.original_amount:
            self.status = self.Status.PARTIAL
        else:
            self.status = self.Status.PAID

    def __str__(self):
        return f"{self.debt_type} - {self.party_name}"
