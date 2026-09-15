from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from business.utils import get_user_business
from business.selectors.dashboard_selectors import (
    get_dashboard_data,
)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = get_user_business(self.request.user)
        data = get_dashboard_data(
            business
        )

        return Response(data)