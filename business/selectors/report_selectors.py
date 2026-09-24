import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import F, Sum

from business.models import Debt, Expense, Product, Sale

# A generous cap on how many points a single series request can produce
# (e.g. ~1 year of daily points). Protects against a client asking for
# period=day over a multi-year range and forcing hundreds of aggregate
# queries in one request.
PERIOD_BUCKET_LIMIT = 366


def _day_buckets(date_from, date_to):
    buckets = []
    current = date_from
    while current <= date_to:
        buckets.append((current, current))
        current += timedelta(days=1)
    return buckets


def _week_buckets(date_from, date_to):
    """Full Monday-Sunday weeks, the same week definition the plain
    dashboard endpoint already uses. A bucket can extend slightly outside
    [date_from, date_to] at the edges so every point is a whole week."""
    buckets = []
    start = date_from - timedelta(days=date_from.weekday())
    while start <= date_to:
        buckets.append((start, start + timedelta(days=6)))
        start += timedelta(days=7)
    return buckets


def _month_buckets(date_from, date_to):
    """Full calendar months, the same month definition the plain dashboard
    endpoint already uses."""
    buckets = []
    year, month = date_from.year, date_from.month
    while date(year, month, 1) <= date_to:
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        buckets.append((start, end))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return buckets


_BUCKET_BUILDERS = {
    "day": _day_buckets,
    "week": _week_buckets,
    "month": _month_buckets,
}


def build_series_buckets(period, date_from, date_to):
    """List of (start, end) inclusive date ranges, one per chart point."""
    return _BUCKET_BUILDERS[period](date_from, date_to)


def get_dashboard_series(business, buckets):
    """Sales/expenses/profit for each (start, end) bucket, oldest first."""
    series = []

    for start, end in buckets:
        sales = Sale.objects.filter(
            business=business,
            sold_at__date__gte=start,
            sold_at__date__lte=end,
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        expenses = Expense.objects.filter(
            business=business,
            expense_date__gte=start,
            expense_date__lte=end,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

        series.append(
            {
                "period": start.isoformat(),
                "sales": sales,
                "expenses": expenses,
                "profit": sales - expenses,
            }
        )

    return series


def get_performance_report(business, date_from, date_to):
    """FR-24: sales/expenses/profit for [date_from, date_to], plus the
    business's current (not date-bound) outstanding balances and stock alerts.

    outstanding_receivables/outstanding_payables calculation, to avoid
    double-counting the same obligation twice:
      - outstanding_receivables comes only from Sale/Payment (total_amount -
        paid_amount for every sale) -- the pre-existing source of truth for
        money owed *to* the business. A Debt with debt_type=RECEIVABLE is
        intentionally NOT added here.
      - outstanding_payables comes only from Debt where debt_type=PAYABLE
        (original_amount - paid_amount) -- money the business owes others.
    Both are live balances (not restricted to date_from/date_to), the same
    way the existing customer-history endpoint reports a live
    outstanding_balance regardless of any date filter.
    """
    total_sales = Sale.objects.filter(
        business=business,
        sold_at__date__gte=date_from,
        sold_at__date__lte=date_to,
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

    total_expenses = Expense.objects.filter(
        business=business,
        expense_date__gte=date_from,
        expense_date__lte=date_to,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    outstanding_receivables = Sale.objects.filter(business=business).aggregate(
        total=Sum(F("total_amount") - F("paid_amount"))
    )["total"] or Decimal("0")

    outstanding_payables = Debt.objects.filter(
        business=business,
        debt_type=Debt.DebtType.PAYABLE,
    ).aggregate(total=Sum(F("original_amount") - F("paid_amount")))["total"] or Decimal("0")

    low_stock_count = Product.objects.filter(
        business=business,
        quantity__lte=F("minimum_stock"),
    ).count()

    return {
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "profit": total_sales - total_expenses,
        "outstanding_receivables": outstanding_receivables,
        "outstanding_payables": outstanding_payables,
        "low_stock_count": low_stock_count,
    }
