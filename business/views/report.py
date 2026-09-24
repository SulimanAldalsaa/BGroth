from datetime import date, timedelta

from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.selectors.dashboard_selectors import get_period_ranges
from business.selectors.report_selectors import (
    PERIOD_BUCKET_LIMIT,
    build_series_buckets,
    get_dashboard_series,
    get_performance_report,
)
from business.serializers.report import (
    DashboardSeriesSerializer,
    PerformanceReportSerializer,
    parse_date_range,
    parse_period,
)
from business.utils import get_user_business


def _series_window_start(period, to):
    """Default trailing window: the last 7 points ending at ``to``."""
    if period == "day":
        return to - timedelta(days=6)
    if period == "week":
        return to - timedelta(weeks=6)

    # month: the 1st of the month 6 months before `to`'s month.
    year, month = to.year, to.month - 6
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


@extend_schema(
    parameters=[
        OpenApiParameter(
            "period", str, enum=["day", "week", "month"],
            description="'day' (default), 'week', or 'month'.",
        ),
        OpenApiParameter(
            "from", OpenApiTypes.DATE,
            description="Start date (YYYY-MM-DD), inclusive. Default: a trailing window of "
            "7 points (days/weeks/months) ending at `to`.",
        ),
        OpenApiParameter(
            "to", OpenApiTypes.DATE,
            description="End date (YYYY-MM-DD), inclusive. Default: today.",
        ),
    ],
    responses={200: DashboardSeriesSerializer},
)
class DashboardSeriesView(APIView):
    """FR-11 / FR-25: sales/expenses/profit as a time series for charting.

    A 'week' point is always a full Monday-Sunday week and a 'month' point a
    full calendar month (same definitions the plain dashboard/ endpoint
    uses), even if that extends slightly outside the requested range.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = get_user_business(request.user)
        period = parse_period(request.query_params.get("period"))

        date_from, date_to = parse_date_range(
            request,
            resolve_default_to=timezone.localdate,
            resolve_default_from=lambda to: _series_window_start(period, to),
        )

        buckets = build_series_buckets(period, date_from, date_to)
        if len(buckets) > PERIOD_BUCKET_LIMIT:
            raise ValidationError(
                {
                    "to": (
                        f"Range is too large for period={period} "
                        f"(maximum {PERIOD_BUCKET_LIMIT} points)."
                    )
                }
            )

        series = get_dashboard_series(business, buckets)
        return Response(DashboardSeriesSerializer({"series": series}).data)


@extend_schema(
    parameters=[
        OpenApiParameter(
            "from", OpenApiTypes.DATE,
            description="Start date (YYYY-MM-DD), inclusive. Default (with no `from`/`to` "
            "at all): the 1st of the current calendar month. If only `to` is given: the "
            "1st of `to`'s month.",
        ),
        OpenApiParameter(
            "to", OpenApiTypes.DATE,
            description="End date (YYYY-MM-DD), inclusive. Default (with no `from`/`to` at "
            "all): the last day of the current calendar month, matching dashboard/'s own "
            "'month' figure. If only `from` is given: today.",
        ),
    ],
    responses={200: PerformanceReportSerializer},
)
class PerformanceReportView(APIView):
    """FR-24: sales/expenses/profit for the period, plus current outstanding
    balances and low-stock count (not restricted to the period)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = get_user_business(request.user)

        # No params at all -> the whole current calendar month, exactly like
        # the plain dashboard/ endpoint's "month" figure (which spans the
        # full month regardless of where "today" falls in it). A partial
        # override (only `from` or only `to`) falls back to `today` / the
        # 1st of that month instead, since "whole month" no longer applies
        # once the caller has picked one side of the range themselves.
        if "from" not in request.query_params and "to" not in request.query_params:
            date_from, date_to = get_period_ranges(timezone.localdate())["month"]
        else:
            date_from, date_to = parse_date_range(
                request,
                resolve_default_to=timezone.localdate,
                resolve_default_from=lambda to: get_period_ranges(to)["month"][0],
            )

        report = get_performance_report(business, date_from, date_to)
        return Response(PerformanceReportSerializer(report).data)
