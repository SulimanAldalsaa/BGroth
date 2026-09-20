import calendar
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from business.models import Expense, Sale


def get_period_ranges(today):
    """Inclusive (start, end) dates for today, this week (Mon-Sun) and this month."""
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    month_end = today.replace(
        day=calendar.monthrange(today.year, today.month)[1]
    )

    return {
        "today": (today, today),
        "week": (week_start, week_start + timedelta(days=6)),
        "month": (month_start, month_end),
    }


def get_dashboard_data(business):
    ranges = get_period_ranges(timezone.localdate())

    sales = Sale.objects.filter(business=business).aggregate(
        **{
            period: Sum(
                "total_amount",
                filter=Q(
                    sold_at__date__gte=start,
                    sold_at__date__lte=end,
                ),
            )
            for period, (start, end) in ranges.items()
        }
    )

    expenses = Expense.objects.filter(business=business).aggregate(
        **{
            period: Sum(
                "amount",
                filter=Q(
                    expense_date__gte=start,
                    expense_date__lte=end,
                ),
            )
            for period, (start, end) in ranges.items()
        }
    )

    data = {}

    for period in ranges:
        period_sales = sales[period] or Decimal("0")
        period_expenses = expenses[period] or Decimal("0")

        data[period] = {
            "sales": period_sales,
            "expenses": period_expenses,
            "profit": period_sales - period_expenses,
        }

    return data
