from django.db import models
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.models import Product, StockMovement
from business.serializers.product import ProductSerializer
from business.services.product_service import create_product
from business.services.stock_service import adjust_stock
from business.utils import get_user_business

class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

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
                business=get_user_business(request.user),
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