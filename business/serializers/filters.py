from rest_framework import serializers


class DateRangeSerializer(serializers.Serializer):
    """Validates the ``date_from`` / ``date_to`` query parameters (YYYY-MM-DD)."""

    date_from = serializers.DateField(
        required=False,
        help_text="Include records on or after this date (YYYY-MM-DD).",
    )
    date_to = serializers.DateField(
        required=False,
        help_text="Include records on or before this date (YYYY-MM-DD).",
    )

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "date_to must not be earlier than date_from."}
            )

        return attrs
