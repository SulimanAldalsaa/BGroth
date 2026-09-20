from django.db import models
from django.db.models import ProtectedError
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.filters import StableOrderingFilter
from business.models import Product, StockMovement
from business.serializers.product import ProductSerializer
from business.serializers.stock import StockAdjustSerializer
from business.services.product_service import create_product
from business.services.stock_service import adjust_stock
from business.utils import get_user_business

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, StableOrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "selling_price", "quantity", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Product.objects.filter(
            business=business
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = get_user_business(request.user)

        product = create_product(
            business=business,
            user=request.user,
            validated_data=serializer.validated_data.copy(),
        )

        output = ProductSerializer(product, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    
class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Product.objects.filter(
            business=business
        )

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This product has sales and cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(request=StockAdjustSerializer, responses={200: ProductSerializer})
class ProductStockAdjustView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = StockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            product = adjust_stock(
                product_id=pk,
                business=get_user_business(request.user),
                user=request.user,
                quantity=data["quantity"],
                movement_type=data["movement_type"],
                reason=data["reason"],
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
        business = get_user_business(self.request.user)
        return Product.objects.filter(
            business=business,
            quantity__lte=models.F("minimum_stock"),
        )


class OutOfStockProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Product.objects.filter(
            business=business,
            quantity=0,
        )