from rest_framework import serializers

PERIOD_CHOICES = ("day", "week", "month")


def parse_period(raw):
    """Validate the ``period`` query parameter; defaults to 'day'."""
    field = serializers.ChoiceField(choices=PERIOD_CHOICES)
    try:
        return field.run_validation(raw if raw is not None else "day")
    except serializers.ValidationError as exc:
        raise serializers.ValidationError({"period": exc.detail})


def parse_date_range(request, *, resolve_default_to, resolve_default_from):
    """Validate the ``from``/``to`` query parameters (YYYY-MM-DD, inclusive).

    A plain function rather than a Serializer: ``from`` is a Python keyword,
    so it cannot be declared as a serializer field's attribute name.

    ``resolve_default_to()`` supplies ``to`` when omitted; ``resolve_default_from(to)``
    supplies ``from`` when omitted, given the (possibly caller-supplied) ``to`` --
    so a default window stays anchored to whatever ``to`` the caller actually gets,
    not always to today.
    """
    date_field = serializers.DateField()
    errors = {}

    raw_to = request.query_params.get("to")
    if raw_to:
        try:
            date_to = date_field.run_validation(raw_to)
        except serializers.ValidationError as exc:
            errors["to"] = exc.detail
            date_to = None
    else:
        date_to = resolve_default_to()

    raw_from = request.query_params.get("from")
    if raw_from:
        try:
            date_from = date_field.run_validation(raw_from)
        except serializers.ValidationError as exc:
            errors["from"] = exc.detail
            date_from = None
    else:
        date_from = resolve_default_from(date_to) if date_to is not None else None

    if errors:
        raise serializers.ValidationError(errors)

    if date_from > date_to:
        raise serializers.ValidationError({"to": "to must not be earlier than from."})

    return date_from, date_to


class SeriesPointSerializer(serializers.Serializer):
    period = serializers.CharField()
    sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit = serializers.DecimalField(max_digits=12, decimal_places=2)


class DashboardSeriesSerializer(serializers.Serializer):
    series = SeriesPointSerializer(many=True)


class PerformanceReportSerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_receivables = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_payables = serializers.DecimalField(max_digits=12, decimal_places=2)
    low_stock_count = serializers.IntegerField()
