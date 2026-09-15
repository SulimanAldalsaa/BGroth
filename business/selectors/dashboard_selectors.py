from django.db.models import Sum
from django.utils import timezone

from business.models import Expense, Sale


def get_dashboard_data(business):
    today = timezone.localdate()

    sales_today = Sale.objects.filter(
        business=business,
        sold_at__date=today,
    ).aggregate(
        total=Sum("total_amount")
    )["total"] or 0

    expenses_today = Expense.objects.filter(
        business=business,
        expense_date=today,
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    return {
        "sales_today": sales_today,
        "expenses_today": expenses_today,
        "profit_today": sales_today - expenses_today,
    }