from django.db import models
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.models import Product, StockMovement
from business.serializers.product import ProductSerializer
from business.services.product_service import create_product
from business.services.stock_service import adjust_stock


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            business=self.request.user.business
        )

    def perform_create(self, serializer):
        create_product(
            business=self.request.user.business,
            user=self.request.user,
            validated_data=serializer.validated_data.copy(),
        )


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            business=self.request.user.business
        )


class ProductStockAdjustView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        quantity = request.data.get("quantity")
        movement_type = request.data.get("movement_type")
        reason = request.data.get("reason", "")

        if quantity is None or movement_type is None:
            return Response(
                {
                    "detail": (
                        "quantity and movement_type are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = adjust_stock(
                product_id=pk,
                business=request.user.business,
                user=request.user,
                quantity=int(quantity),
                movement_type=movement_type,
                reason=reason,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            ProductSerializer(product).data
        )


class LowStockProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            business=self.request.user.business,
            quantity__lte=models.F("minimum_stock"),
        )


class OutOfStockProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            business=self.request.user.business,
            quantity=0,
        )