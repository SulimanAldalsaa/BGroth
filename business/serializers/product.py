from rest_framework import serializers

from business.models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "selling_price",
            "cost_price",
            "quantity",
            "minimum_stock",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        selling_price = attrs.get(
            "selling_price",
            getattr(self.instance, "selling_price", None),
        )

        cost_price = attrs.get(
            "cost_price",
            getattr(self.instance, "cost_price", None),
        )

        if (
            selling_price is not None
            and cost_price is not None
            and selling_price < cost_price
        ):
            raise serializers.ValidationError(
                {
                    "selling_price": (
                        "Selling price cannot be lower than cost price."
                    )
                }
            )

        return attrs