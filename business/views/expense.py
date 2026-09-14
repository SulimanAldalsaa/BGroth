from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.models import Expense
from business.serializers import ExpenseSerializer


class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(
            business=self.request.user.business
        ).order_by(
            "-date",
            "-created_at",
        )

    def perform_create(self, serializer):
        serializer.save(
            business=self.request.user.business
        )


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(
            business=self.request.user.business
        )