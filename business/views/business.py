from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.serializers.business import (
    BusinessCreateSerializer,
    BusinessSerializer,
)


class BusinessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = getattr(request.user, "business", None)

        if not business:
            return Response(
                {"detail": "Business not found."},
                status=404,
            )

        serializer = BusinessSerializer(business)
        return Response(serializer.data)

    def post(self, request):
        serializer = BusinessCreateSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)
        business = serializer.save(owner=request.user)

        return Response(
            BusinessSerializer(business).data,
            status=201,
        )

    def patch(self, request):
        business = getattr(request.user, "business", None)

        if not business:
            return Response(
                {"detail": "Business not found."},
                status=404,
            )

        serializer = BusinessSerializer(
            business,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)