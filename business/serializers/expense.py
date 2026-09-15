from rest_framework import serializers

from business.models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            "id",
            "amount",
            "category",
            "description",
            "expense_date",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]