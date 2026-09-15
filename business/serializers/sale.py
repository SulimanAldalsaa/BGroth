from rest_framework import serializers

from business.models import Sale, SaleItem


class SaleItemCreateSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class SaleCreateSerializer(serializers.Serializer):
    customer = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    paid_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        default=0,
    )

    items = SaleItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one item is required."
            )

        return value


class SaleItemResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = [
            "id",
            "product",
            "quantity",
            "unit_price",
            "subtotal",
        ]


class SaleResponseSerializer(serializers.ModelSerializer):
    items = SaleItemResponseSerializer(many=True, read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Sale
        fields = [
            "id",
            "customer",
            "total_amount",
            "paid_amount",
            "remaining_amount",
            "payment_status",
            "sold_at",
            "items",
        ]