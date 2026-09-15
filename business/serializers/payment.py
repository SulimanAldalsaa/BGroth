from rest_framework import serializers

from business.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "amount",
            "payment_method",
            "note",
            "payment_date",
        ]
        read_only_fields = [
            "id",
            "payment_date",
        ]