from django.db import models
from django.db.models import Q


class InvoiceNumberSequence(models.Model):
    """Per-business, per-day counter used to generate ``INV-YYYYMMDD-0001`` numbers.

    Numbers are allocated by locking this row (``select_for_update``) inside the
    invoice-creation transaction, so two concurrent requests can never receive
    the same number even if they land on the same business and day.
    """

    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="invoice_number_sequences",
    )
    date = models.DateField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "date"],
                name="unique_invoice_sequence_per_business_per_day",
            )
        ]

    def __str__(self):
        return f"{self.business_id} {self.date} -> {self.last_number}"


class Invoice(models.Model):

    class Status(models.TextChoices):
        ISSUED = "ISSUED", "Issued"
        CANCELLED = "CANCELLED", "Cancelled"

    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    # At most one ISSUED invoice per sale at a time (BR-11), enforced by the
    # partial unique constraint below -- a plain OneToOneField would make it
    # impossible to ever issue a replacement invoice after cancelling one for
    # the same sale, which BR-12/AC-5 require ("cancel + reissue"). PROTECT so
    # an invoice (issued or cancelled) can never be orphaned by a sale
    # deletion; views must handle ProtectedError explicitly, the same way
    # Product already does for SaleItem.
    sale = models.ForeignKey(
        "business.Sale",
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    invoice_number = models.CharField(max_length=30, editable=False)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED,
    )

    issued_at = models.DateTimeField(auto_now_add=True)

    # Snapshot fields (BR-12): frozen at issue time, independent of later
    # changes to the customer or sale/product records.
    customer_name = models.CharField(max_length=255, blank=True)
    customer_phone = models.CharField(max_length=30, blank=True)

    total = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business", "invoice_number"],
                name="unique_invoice_number_per_business",
            ),
            # BR-11: only one *active* invoice per sale. Cancelled invoices
            # for the same sale don't count, so a new one can be issued after
            # cancellation (BR-12's "cancel and reissue"). Uses the literal
            # "ISSUED" value (must match Status.ISSUED) because a nested
            # class body -- Meta here -- cannot see sibling names (Status)
            # from the enclosing Invoice class by plain name lookup.
            models.UniqueConstraint(
                fields=["sale"],
                condition=Q(status="ISSUED"),
                name="unique_issued_invoice_per_sale",
            ),
        ]
        indexes = [
            models.Index(fields=["business", "issued_at"]),
        ]

    def __str__(self):
        return self.invoice_number
