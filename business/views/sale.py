from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from business.serializers import (
    SaleCreateSerializer,
    SaleResponseSerializer,
)
from business.selectors.sale_selectors import (
    get_business_sales,
)
from business.services.sale_service import SaleService


class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SaleCreateSerializer

        return SaleResponseSerializer

    def get_queryset(self):
        return get_business_sales(
            self.request.user.business
        )

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        sale = SaleService.create_sale(
            business=request.user.business,
            customer_id=serializer.validated_data.get(
                "customer"
            ),
            paid_amount=serializer.validated_data[
                "paid_amount"
            ],
            items=serializer.validated_data["items"],
        )

        response_serializer = SaleResponseSerializer(
            sale
        )

        return Response(
            response_serializer.data,
            status=201,
        )