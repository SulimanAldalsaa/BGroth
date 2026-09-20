from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.filters import StableOrderingFilter
from business.models import Customer
from business.selectors.customer_selectors import (
    get_customer_sales,
    get_customer_summary,
)
from business.serializers.customer import (
    CustomerHistorySerializer,
    CustomerSerializer,
)
from business.utils import get_user_business

class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, StableOrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

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


@extend_schema(responses={200: CustomerHistorySerializer})
class CustomerHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        customer = get_object_or_404(
            Customer,
            pk=pk,
            business=get_user_business(request.user),
        )

        data = {
            "customer": customer,
            "summary": get_customer_summary(customer),
            "sales": get_customer_sales(customer),
        }

        return Response(CustomerHistorySerializer(data).data)
