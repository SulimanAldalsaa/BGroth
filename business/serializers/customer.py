from rest_framework import serializers

from business.models import Customer
from business.serializers.sale import SaleResponseSerializer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class CustomerSummarySerializer(serializers.Serializer):
    total_purchases = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=14, decimal_places=2)


class CustomerHistorySerializer(serializers.Serializer):
    customer = CustomerSerializer()
    summary = CustomerSummarySerializer()
    sales = SaleResponseSerializer(many=True)
