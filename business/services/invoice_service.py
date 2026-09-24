from django.db import transaction
from django.utils import timezone

from business.models import Invoice, InvoiceItem, InvoiceNumberSequence, Sale


def _allocate_invoice_number(*, business, today):
    """Return the next ``INV-YYYYMMDD-0001`` number for this business/day.

    Locks the per-(business, date) counter row for the duration of the caller's
    transaction, so two concurrent requests are serialized and never receive the
    same number (get_or_create already retries safely if the row does not exist
    yet and two transactions race to create it).
    """
    sequence, _ = InvoiceNumberSequence.objects.select_for_update().get_or_create(
        business=business,
        date=today,
    )
    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])
    return f"INV-{today.strftime('%Y%m%d')}-{sequence.last_number:04d}"


@transaction.atomic
def create_invoice_from_sale(*, sale, business, notes=""):
    """Create an immutable Invoice + InvoiceItem snapshot from an existing Sale.

    ``sale`` must already be scoped to ``business`` by the caller (404 for a
    missing/foreign sale is the view's job); this only enforces the invoicing
    business rules (BR-11: at most one *active* invoice per sale) and the
    snapshot (BR-12). A sale whose only invoice was cancelled is eligible
    again, which is how BR-12's "cancel and reissue" is satisfied.
    """
    # select_for_update() cannot be combined with select_related("customer"):
    # customer is a nullable FK, and Postgres refuses FOR UPDATE across the
    # nullable side of an outer join. Lock the Sale row alone, then read the
    # customer/items as separate queries.
    sale = Sale.objects.select_for_update().get(pk=sale.pk)

    if Invoice.objects.filter(sale=sale, status=Invoice.Status.ISSUED).exists():
        raise ValueError("An invoice already exists for this sale.")

    items = list(sale.items.select_related("product").all())

    today = timezone.localdate()
    invoice_number = _allocate_invoice_number(business=business, today=today)

    invoice = Invoice.objects.create(
        business=business,
        sale=sale,
        invoice_number=invoice_number,
        customer_name=sale.customer.name if sale.customer else "",
        customer_phone=sale.customer.phone if sale.customer else "",
        total=sale.total_amount,
        notes=notes,
    )

    InvoiceItem.objects.bulk_create(
        [
            InvoiceItem(
                invoice=invoice,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.subtotal,
            )
            for item in items
        ]
    )

    return invoice


@transaction.atomic
def cancel_invoice(*, invoice):
    """Move ISSUED -> CANCELLED. State change only: never touches Sale/Payment/stock."""
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

    if invoice.status == Invoice.Status.CANCELLED:
        raise ValueError("Invoice is already cancelled.")

    invoice.status = Invoice.Status.CANCELLED
    invoice.save(update_fields=["status"])
    return invoice
