from datetime import timedelta

from django.utils import timezone

from business.models import Debt


def get_due_debts(business, days):
    """Debts due from today through today + ``days`` (inclusive), excluding PAID."""
    today = timezone.localdate()
    end_date = today + timedelta(days=days)

    return (
        Debt.objects.filter(
            business=business,
            due_date__isnull=False,
            due_date__gte=today,
            due_date__lte=end_date,
        )
        .exclude(status=Debt.Status.PAID)
        .order_by("due_date")
    )
