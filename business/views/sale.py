from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from business.serializers.sale import (
    SaleCreateSerializer,
    SaleResponseSerializer,
    SaleUpdateSerializer,
)
from business.services.sale_service import (
    create_sale,
    update_sale,
    delete_sale,
)
from business.utils import get_user_business   # لو عملت الـ helper


class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return (
            __import__("business.models", fromlist=["Sale"]).Sale.objects
            .filter(business=business)
            .prefetch_related("items")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SaleCreateSerializer
        return SaleResponseSerializer

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = get_user_business(request.user)

        try:
            sale = create_sale(
                business=business,
                user=request.user,
                customer_id=serializer.validated_data.get("customer"),
                paid_amount=serializer.validated_data["paid_amount"],
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


class SaleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        from business.models import Sale
        return Sale.objects.filter(
            business=business
        ).prefetch_related("items")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return SaleUpdateSerializer
        return SaleResponseSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = SaleUpdateSerializer(
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        business = get_user_business(request.user)

        try:
            sale = update_sale(
                sale_id=kwargs["pk"],
                business=business,
                user=request.user,
                customer_id=serializer.validated_data.get("customer"),
                paid_amount=serializer.validated_data.get("paid_amount"),
                items=serializer.validated_data.get("items"),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(SaleResponseSerializer(sale).data)

    def destroy(self, request, *args, **kwargs):
        business = get_user_business(request.user)

        try:
            delete_sale(
                sale_id=kwargs["pk"],
                business=business,
                user=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)