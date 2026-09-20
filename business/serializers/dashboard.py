from rest_framework import serializers


class DashboardSerializer(serializers.Serializer):
    sales_today = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses_today = serializers.DecimalField(max_digits=14, decimal_places=2)
    profit_today = serializers.DecimalField(max_digits=14, decimal_places=2)
