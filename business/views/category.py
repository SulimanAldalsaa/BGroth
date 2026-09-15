from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Category
from business.serializers.category import CategorySerializer
from business.utils import get_user_business

class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Category.objects.filter(
            business=business
        )

    def perform_create(self, serializer):
        business = get_user_business(self.request.user)
        serializer.save(
            business=business
        )


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Category.objects.filter(
            business=business
        )