from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Product
from business.serializers import ProductSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            business=self.request.user.business
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business
        )


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(
            business=self.request.user.business
        )