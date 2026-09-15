from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Expense
from business.serializers.expense import ExpenseSerializer


class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Expense.objects.filter(
            business=self.request.user.business
        )

        category = self.request.query_params.get("category")

        if category:
            queryset = queryset.filter(
                category=category
            )

        return queryset

    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business
        )


class ExpenseDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(
            business=self.request.user.business
        )