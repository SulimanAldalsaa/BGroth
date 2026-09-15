from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Category
from business.serializers.category import CategorySerializer


class CategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            business__owner=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business
        )


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            business__owner=self.request.user
        )