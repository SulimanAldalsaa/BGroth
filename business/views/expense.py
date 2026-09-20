from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from business.filters import StableOrderingFilter, filter_by_date_range
from business.models import Expense
from business.pagination import OptionalPageNumberPagination
from business.serializers.expense import ExpenseSerializer
from business.serializers.filters import DateRangeSerializer
from business.utils import get_user_business

@extend_schema_view(
    get=extend_schema(
        parameters=[
            DateRangeSerializer,
            OpenApiParameter(
                "category",
                str,
                description="Only expenses with exactly this category.",
            ),
        ]
    )
)
class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination
    filter_backends = [StableOrderingFilter]
    ordering_fields = ["expense_date", "amount", "created_at"]
    ordering = ["-expense_date"]

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

        return filter_by_date_range(
            queryset,
            self.request,
            "expense_date",
        )

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
