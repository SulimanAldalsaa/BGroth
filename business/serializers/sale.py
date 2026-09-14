from rest_framework import serializers

from business.models import Sale


class SaleItemInputSerializer(serializers.Serializer):
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
    )

    items = SaleItemInputSerializer(
        many=True,
        allow_empty=False,
    )


class SaleItemResponseSerializer(serializers.Serializer):
    product = serializers.IntegerField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    subtotal = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )


class SaleResponseSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

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
            "items",
            "created_at",
        ]

    def get_items(self, obj):
        return [
            {
                "product": item.product.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
            }
            for item in obj.items.all()
        ]

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
            "items",
            "created_at",
        ]