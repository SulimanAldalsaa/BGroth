from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from business.selectors.dashboard_selectors import (
    get_dashboard_data,
)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_dashboard_data(
            request.user.business
        )

        return Response(data)