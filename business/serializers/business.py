from rest_framework import serializers

from business.models import Business


class BusinessCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            "name",
            "description",
            "phone",
            "address",
            "city",
            "country",
        ]

    def validate(self, attrs):
        request = self.context["request"]

        if Business.objects.filter(owner=request.user).exists():
            raise serializers.ValidationError(
                "You already have a business."
            )

        return attrs


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "description",
            "phone",
            "address",
            "city",
            "country",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]