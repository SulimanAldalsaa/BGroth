from rest_framework import serializers

from business.models import Category
from business.utils import get_user_business

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        request = self.context["request"]

        business = get_user_business(request.user)

        queryset = Category.objects.filter(
            business=business,
            name=value,
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "This category already exists."
            )

        return value