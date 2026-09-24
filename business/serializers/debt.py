from decimal import Decimal

from rest_framework import serializers

from business.models import Debt, DebtPayment


class DebtSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Debt
        fields = [
            "id",
            "debt_type",
            "party_name",
            "customer",
            "sale",
            "original_amount",
            "paid_amount",
            "remaining_amount",
            "due_date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "paid_amount",
            "status",
            "created_at",
            "updated_at",
        ]


class DebtCreateSerializer(serializers.Serializer):
    debt_type = serializers.ChoiceField(choices=Debt.DebtType.choices)
    party_name = serializers.CharField(max_length=255)
    customer = serializers.IntegerField(required=False, allow_null=True)
    sale = serializers.IntegerField(required=False, allow_null=True)
    original_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
    )
    due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
    )


class DebtUpdateSerializer(serializers.Serializer):
    # Money/derived fields are never editable here; see business/services/debt_service.py.
    NOT_EDITABLE_FIELDS = (
        "paid_amount",
        "status",
        "debt_type",
        "original_amount",
        "customer",
        "sale",
        "business",
    )

    party_name = serializers.CharField(required=False, max_length=255)
    due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs):
        rejected = {
            field: (
                "This field cannot be edited. "
                "Record payments with POST /api/business/debts/{id}/payments/."
            )
            for field in self.NOT_EDITABLE_FIELDS
            if field in self.initial_data
        }

        if rejected:
            raise serializers.ValidationError(rejected)

        return attrs


class DebtPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtPayment
        fields = ["id", "debt", "amount", "note", "created_at"]
        read_only_fields = ["id", "debt", "created_at"]


class DebtPaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=255,
    )
