from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Customer, Sale
from business.serializers.customer import CustomerSerializer
from business.serializers.sale import SaleResponseSerializer
from business.utils import get_user_business

class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Customer.objects.filter(
            business=business
        )

    def perform_create(self, serializer):
        business = get_user_business(self.request.user)
        serializer.save(
            business=business
        )


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Customer.objects.filter(
            business=business
        )


class CustomerHistoryView(generics.ListAPIView):
    serializer_class = SaleResponseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Sale.objects.filter(
            business=business,
            customer_id=self.kwargs["pk"],
        ).prefetch_related("items")