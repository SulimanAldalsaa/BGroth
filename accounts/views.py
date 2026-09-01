from django.conf import settings
from django.core.mail import send_mail
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from .models import PasswordResetToken, User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
    AuthResponseSerializer,
    MessageResponseSerializer,
)



def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


# REGISTER
@extend_schema(responses={201: AuthResponseSerializer})
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data, "tokens": _tokens_for_user(user)},
            status=status.HTTP_201_CREATED,
        )


# LOGIN
@extend_schema(request=LoginSerializer, responses={200: AuthResponseSerializer})
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response(
            {"user": UserSerializer(user).data, "tokens": _tokens_for_user(user)},
            status=status.HTTP_200_OK,
        )


# LOGOUT
@extend_schema(request=TokenRefreshSerializer, responses={200: MessageResponseSerializer})
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response(
                {"error": "Invalid or already expired token."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


# CURRENT USER / CHANGE PASSWORD

@extend_schema(responses={200: UserSerializer})
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

@extend_schema(request=ChangePasswordSerializer, responses={200: MessageResponseSerializer})
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


# FORGOT PASSWORD

class PasswordResetRequestThrottle(AnonRateThrottle):
    rate = "5/hour"

@extend_schema(request=PasswordResetRequestSerializer, responses={200: MessageResponseSerializer})
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            reset_token = PasswordResetToken.objects.create(user=user)
            reset_link = f"{settings.FRONTEND_RESET_PASSWORD_URL}?token={reset_token.token}"

            send_mail(
                subject="Reset your password",
                message=(
                    "Use the link below to reset your password:\n\n"
                    f"{reset_link}\n\n"
                    "This link expires soon. If you did not request this, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        return Response(
            {"message": "If an account with this email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )

@extend_schema(request=PasswordResetConfirmSerializer, responses={200: MessageResponseSerializer})
class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/
    body: { "token", "new_password", "new_password_confirm" }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reset_token = serializer.validated_data["reset_token"]
        new_password = serializer.validated_data["new_password"]

        user = reset_token.user
        user.set_password(new_password)
        user.save(update_fields=["password"])

        reset_token.used = True
        reset_token.save(update_fields=["used"])

        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

        return Response(
            {"message": "Password has been reset successfully. Please log in."},
            status=status.HTTP_200_OK,
        )
