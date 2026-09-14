from rest_framework import serializers
from business.models import Business


class BusinessCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ["name", "description"]


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]