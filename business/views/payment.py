from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.serializers.payment import PaymentSerializer
from business.services.payment_service import add_payment


class PaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sale_id):
        serializer = PaymentSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            payment = add_payment(
                sale_id=sale_id,
                business=request.user.business,
                amount=serializer.validated_data["amount"],
                payment_method=serializer.validated_data[
                    "payment_method"
                ],
                note=serializer.validated_data.get(
                    "note",
                    "",
                ),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )