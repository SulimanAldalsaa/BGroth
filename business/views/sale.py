from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from business.models import Sale
from business.serializers.sale import (
    SaleCreateSerializer,
    SaleResponseSerializer,
)
from business.services.sale_service import create_sale


class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Sale.objects.filter(
            business=self.request.user.business
        ).prefetch_related("items")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SaleCreateSerializer

        return SaleResponseSerializer

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            sale = create_sale(
                business=request.user.business,
                user=request.user,
                customer_id=serializer.validated_data.get(
                    "customer"
                ),
                paid_amount=serializer.validated_data[
                    "paid_amount"
                ],
                items=serializer.validated_data["items"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            SaleResponseSerializer(sale).data,
            status=status.HTTP_201_CREATED,
        )


class SaleDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SaleResponseSerializer

    def get_queryset(self):
        return Sale.objects.filter(
            business=self.request.user.business
        ).prefetch_related("items")