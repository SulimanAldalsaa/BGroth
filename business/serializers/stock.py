from rest_framework import serializers

from business.models import StockMovement


class StockAdjustSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)
    movement_type = serializers.ChoiceField(
        choices=[
            StockMovement.MovementType.IN,
            StockMovement.MovementType.OUT,
            StockMovement.MovementType.ADJUSTMENT,
        ]
    )
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        default="",
    )
