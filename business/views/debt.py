from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.filters import StableOrderingFilter
from business.models import Debt
from business.selectors.debt_selectors import get_due_debts
from business.serializers.debt import (
    DebtCreateSerializer,
    DebtPaymentCreateSerializer,
    DebtPaymentSerializer,
    DebtSerializer,
    DebtUpdateSerializer,
)
from business.services.debt_service import add_debt_payment, create_debt, update_debt
from business.utils import get_user_business


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                "type", str, enum=["RECEIVABLE", "PAYABLE"],
                description="Only debts with this debt_type.",
            ),
            OpenApiParameter(
                "status", str, enum=["UNPAID", "PARTIAL", "PAID"],
                description="Only debts with this status.",
            ),
            OpenApiParameter(
                "due_before", OpenApiTypes.DATE,
                description="Only debts due on or before this date (YYYY-MM-DD).",
            ),
        ]
    ),
    # The view returns DebtSerializer's output on create (paid_amount, status,
    # remaining_amount, timestamps, ...), not an echo of the DebtCreate input,
    # so the response schema needs to say so explicitly.
    post=extend_schema(responses={201: DebtSerializer}),
)
class DebtListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, StableOrderingFilter]
    search_fields = ["party_name"]
    ordering_fields = ["due_date", "original_amount", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DebtCreateSerializer
        return DebtSerializer

    def get_queryset(self):
        business = get_user_business(self.request.user)
        queryset = Debt.objects.filter(business=business)

        debt_type = self.request.query_params.get("type")
        if debt_type:
            queryset = queryset.filter(debt_type=debt_type)

        debt_status = self.request.query_params.get("status")
        if debt_status:
            queryset = queryset.filter(status=debt_status)

        due_before = self.request.query_params.get("due_before")
        if due_before:
            parsed = parse_date(due_before)
            if parsed is None:
                raise ValidationError(
                    {"due_before": "Date has wrong format. Use YYYY-MM-DD."}
                )
            queryset = queryset.filter(due_date__lte=parsed)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = DebtCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            debt = create_debt(
                business=get_user_business(request.user),
                debt_type=serializer.validated_data["debt_type"],
                party_name=serializer.validated_data["party_name"],
                original_amount=serializer.validated_data["original_amount"],
                customer_id=serializer.validated_data.get("customer"),
                sale_id=serializer.validated_data.get("sale"),
                due_date=serializer.validated_data.get("due_date"),
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            DebtSerializer(debt).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    # update() always responds with the full Debt (paid_amount, status,
    # remaining_amount, timestamps, ...), not an echo of the DebtUpdate input.
    put=extend_schema(responses={200: DebtSerializer}),
    patch=extend_schema(responses={200: DebtSerializer}),
)
class DebtDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Debt.objects.filter(business=business)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return DebtUpdateSerializer
        return DebtSerializer

    def update(self, request, *args, **kwargs):
        debt = self.get_object()  # 404 for debts of other businesses
        partial = kwargs.pop("partial", False)
        serializer = DebtUpdateSerializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        debt = update_debt(debt=debt, **serializer.validated_data)
        return Response(DebtSerializer(debt).data)


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                "days", int,
                description="Debts due from today through today + this many days (inclusive). "
                "Default: 7. Must be a non-negative integer.",
            ),
        ]
    )
)
class DebtDueListView(generics.ListAPIView):
    serializer_class = DebtSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)

        raw_days = self.request.query_params.get("days", "7")
        try:
            days = int(raw_days)
        except (TypeError, ValueError):
            raise ValidationError({"days": "Must be an integer."})

        if days < 0:
            raise ValidationError({"days": "Must not be negative."})

        return get_due_debts(business, days)


@extend_schema(request=DebtPaymentCreateSerializer, responses={201: DebtPaymentSerializer})
class DebtPaymentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, debt_id):
        business = get_user_business(request.user)
        debt = get_object_or_404(Debt, id=debt_id, business=business)

        serializer = DebtPaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = add_debt_payment(
                debt=debt,
                amount=serializer.validated_data["amount"],
                note=serializer.validated_data.get("note", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            DebtPaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )
