from rest_framework import serializers

from business.models import Invoice, InvoiceItem


class InvoiceCreateSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
    )


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = [
            "id",
            "product_name",
            "quantity",
            "unit_price",
            "line_total",
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "sale",
            "invoice_number",
            "status",
            "issued_at",
            "customer_name",
            "customer_phone",
            "total",
            "notes",
            "items",
        ]
        read_only_fields = fields
