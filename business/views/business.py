from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from business.serializers import (
    BusinessCreateSerializer,
    BusinessSerializer,
)
from business.services.business_service import (
    BusinessService,
)


class BusinessView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = getattr(
            request.user,
            "business",
            None,
        )

        if business is None:
            return Response(
                {
                    "detail": (
                        "Business has not been created."
                    )
                },
                status=404,
            )

        serializer = BusinessSerializer(
            business
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = BusinessCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        business = BusinessService.create_business(
            owner=request.user,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get(
                "description",
                "",
            ),
        )

        response_serializer = BusinessSerializer(
            business
        )

        return Response(
            response_serializer.data,
            status=201,
        )

    def patch(self, request):
        business = getattr(
            request.user,
            "business",
            None,
        )

        if business is None:
            return Response(
                {
                    "detail": (
                        "Business has not been created."
                    )
                },
                status=404,
            )

        serializer = BusinessSerializer(
            business,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data
        )