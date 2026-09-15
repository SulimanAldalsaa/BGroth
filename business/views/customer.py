from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Customer, Sale
from business.serializers.customer import CustomerSerializer
from business.serializers.sale import SaleResponseSerializer


class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.filter(
            business=self.request.user.business
        )

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


class CustomerHistoryView(generics.ListAPIView):
    serializer_class = SaleResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Sale.objects.filter(
            business=self.request.user.business,
            customer_id=self.kwargs["pk"],
        ).prefetch_related("items")