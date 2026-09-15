from rest_framework import serializers

from business.models import Category, Product


class ProductSerializer(serializers.ModelSerializer):
    initial_quantity = serializers.IntegerField(
        required=False,
        min_value=0,
        write_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "name",
            "description",
            "selling_price",
            "cost_price",
            "quantity",
            "minimum_stock",
            "image",
            "initial_quantity",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "quantity",
            "created_at",
            "updated_at",
        ]

    def validate_category(self, category):
        request = self.context["request"]

        if category and category.business.owner != request.user:
            raise serializers.ValidationError(
                "Invalid category."
            )

        return category