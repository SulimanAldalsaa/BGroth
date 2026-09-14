from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Customer
from business.serializers import CustomerSerializer


class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.filter(
            business=self.request.user.business
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business
        )


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.filter(
            business=self.request.user.business
        )