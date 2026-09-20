from rest_framework import serializers


class DashboardPeriodSerializer(serializers.Serializer):
    sales = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    profit = serializers.DecimalField(max_digits=14, decimal_places=2)


class DashboardSerializer(serializers.Serializer):
    today = DashboardPeriodSerializer()
    week = DashboardPeriodSerializer()
    month = DashboardPeriodSerializer()

    # Deprecated flat aliases of ``today``, kept for existing clients.
    sales_today = serializers.DecimalField(
        max_digits=14, decimal_places=2, source="today.sales"
    )
    expenses_today = serializers.DecimalField(
        max_digits=14, decimal_places=2, source="today.expenses"
    )
    profit_today = serializers.DecimalField(
        max_digits=14, decimal_places=2, source="today.profit"
    )
