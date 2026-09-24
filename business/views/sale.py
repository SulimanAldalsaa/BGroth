from django.db.models import ProtectedError
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from business.filters import StableOrderingFilter, filter_by_date_range
from business.models import Sale
from business.pagination import OptionalPageNumberPagination
from business.serializers.filters import DateRangeSerializer
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
from business.utils import get_user_business


@extend_schema_view(get=extend_schema(parameters=[DateRangeSerializer]))
class SaleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination
    filter_backends = [StableOrderingFilter]
    ordering_fields = ["sold_at", "total_amount", "paid_amount"]
    ordering = ["-sold_at"]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        queryset = Sale.objects.filter(
            business=business
        ).prefetch_related("items")

        return filter_by_date_range(
            queryset,
            self.request,
            "sold_at__date",
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
        return Sale.objects.filter(
            business=business
        ).prefetch_related("items")

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return SaleUpdateSerializer
        return SaleResponseSerializer

    def update(self, request, *args, **kwargs):
        self.get_object()  # 404 for sales of other businesses
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
                items=serializer.validated_data.get("items"),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(SaleResponseSerializer(sale).data)

    def destroy(self, request, *args, **kwargs):
        self.get_object()  # 404 for sales of other businesses
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
        except ProtectedError:
            return Response(
                {"detail": "This sale has an invoice and cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
