from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Expense
from business.serializers.expense import ExpenseSerializer
from business.utils import get_user_business

class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        queryset = Expense.objects.filter(
            business=business
        )

        category = self.request.query_params.get("category")

        if category:
            queryset = queryset.filter(
                category=category
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            business=get_user_business(self.request.user)
        )


class ExpenseDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Expense.objects.filter(
            business=business
        )