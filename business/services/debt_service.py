from decimal import Decimal

from django.db import transaction

from business.models import Customer, Debt, DebtPayment, Sale


@transaction.atomic
def create_debt(
    *,
    business,
    debt_type,
    party_name,
    original_amount,
    customer_id=None,
    sale_id=None,
    due_date=None,
    notes="",
):
    customer = None
    if customer_id:
        customer = Customer.objects.filter(id=customer_id, business=business).first()
        if customer is None:
            raise ValueError("Invalid customer.")

    sale = None
    if sale_id:
        sale = Sale.objects.filter(id=sale_id, business=business).first()
        if sale is None:
            raise ValueError("Invalid sale.")

    debt = Debt.objects.create(
        business=business,
        debt_type=debt_type,
        party_name=party_name,
        customer=customer,
        sale=sale,
        original_amount=original_amount,
        due_date=due_date,
        notes=notes,
    )
    debt.recalculate_status()
    debt.save(update_fields=["status"])
    return debt


@transaction.atomic
def update_debt(*, debt, **fields):
    """Apply only logically-mutable fields (party_name/due_date/notes).

    ``paid_amount``/``status`` are intentionally not accepted here — mirrors
    the existing Sale convention where money fields are rejected by the
    serializer and can only change through the dedicated payment endpoint.
    """
    debt = Debt.objects.select_for_update().get(pk=debt.pk)

    for field, value in fields.items():
        setattr(debt, field, value)

    debt.save()
    return debt


@transaction.atomic
def add_debt_payment(*, debt, amount, note=""):
    debt = Debt.objects.select_for_update().get(pk=debt.pk)

    amount = Decimal(amount)

    if amount <= 0:
        raise ValueError("Payment must be greater than zero.")

    remaining = debt.original_amount - debt.paid_amount

    if amount > remaining:
        raise ValueError("Payment cannot exceed remaining amount.")

    payment = DebtPayment.objects.create(debt=debt, amount=amount, note=note)

    debt.paid_amount += amount
    debt.recalculate_status()
    debt.save(update_fields=["paid_amount", "status", "updated_at"])

    return payment
