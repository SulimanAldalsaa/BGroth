from rest_framework.filters import OrderingFilter

from business.serializers.filters import DateRangeSerializer


class StableOrderingFilter(OrderingFilter):
    """OrderingFilter that always ends with the primary key.

    Rows with equal values keep a fixed order, so pages never overlap.
    """

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)
        return queryset.order_by(*queryset.query.order_by, "pk")


def filter_by_date_range(queryset, request, field):
    """Apply ``date_from`` / ``date_to`` query parameters to ``field``.

    Invalid values raise a 400 validation error naming the parameter.
    """
    params = DateRangeSerializer(data=request.query_params)
    params.is_valid(raise_exception=True)

    date_from = params.validated_data.get("date_from")
    date_to = params.validated_data.get("date_to")

    if date_from:
        queryset = queryset.filter(**{f"{field}__gte": date_from})

    if date_to:
        queryset = queryset.filter(**{f"{field}__lte": date_to})

    return queryset
