from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.filters import StableOrderingFilter, filter_by_date_range
from business.models import Invoice, Sale
from business.pagination import OptionalPageNumberPagination
from business.serializers.filters import DateRangeSerializer
from business.serializers.invoice import InvoiceCreateSerializer, InvoiceSerializer
from business.services.invoice_pdf import render_invoice_pdf
from business.services.invoice_service import cancel_invoice, create_invoice_from_sale
from business.utils import get_user_business


@extend_schema(request=InvoiceCreateSerializer, responses={201: InvoiceSerializer})
class InvoiceCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, sale_id):
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = get_user_business(request.user)
        sale = get_object_or_404(Sale, id=sale_id, business=business)

        try:
            invoice = create_invoice_from_sale(
                sale=sale,
                business=business,
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            InvoiceSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(get=extend_schema(parameters=[DateRangeSerializer]))
class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination
    filter_backends = [StableOrderingFilter]
    ordering_fields = ["issued_at", "total"]
    ordering = ["-issued_at"]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        queryset = Invoice.objects.filter(business=business).prefetch_related("items")
        return filter_by_date_range(queryset, self.request, "issued_at__date")


class InvoiceDetailView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        business = get_user_business(self.request.user)
        return Invoice.objects.filter(business=business).prefetch_related("items")


@extend_schema(request=None, responses={200: InvoiceSerializer})
class InvoiceCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        business = get_user_business(request.user)
        invoice = get_object_or_404(Invoice, pk=pk, business=business)

        try:
            invoice = cancel_invoice(invoice=invoice)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(InvoiceSerializer(invoice).data)


@extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
class InvoicePdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        business = get_user_business(request.user)
        invoice = get_object_or_404(
            Invoice.objects.prefetch_related("items"),
            pk=pk,
            business=business,
        )

        pdf_bytes = render_invoice_pdf(invoice, business)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="{invoice.invoice_number}.pdf"'
        )
        return response
