from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from apps.base.auth import JWTTokenGenerator
from apps.user.models import User
from apps.user.serializers import (
    RefreshTokenSerializer, UserProfileSerializer,
    RefreshResponseSerializer, LogoutResponseSerializer,
    ErrorSerializer, OTPLoginSerializer, OTPLoginResponseSerializer
)
from apps.base.redis_service import redis_service
from drf_spectacular.utils import extend_schema, OpenApiExample


class LoginView(APIView):
    """
    OTP-based login endpoint (main login method)
    """
    permission_classes = [AllowAny]
    serializer_class = OTPLoginSerializer
    
    @extend_schema(
        operation_id='user_login',
        summary='User Login (OTP)',
        description='Login using OTP code received from Telegram bot. This is the main login method.',
        request=OTPLoginSerializer,
        responses={
            200: OTPLoginResponseSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
        },
        examples=[
            OpenApiExample(
                'OTP Login Request',
                summary='OTP login request',
                description='Example OTP login request - only OTP code needed',
                value={
                    'otp': '123456'
                },
                request_only=True
            ),
            OpenApiExample(
                'OTP Login Success Response',
                summary='Successful OTP login response',
                description='Response when OTP login is successful',
                value={
                    'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'user': {
                        'id': '01HZ8X9K2M3N4P5Q6R7S8T9U0V',
                        'phone_number': '998931159963',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'email': 'john@example.com',
                        'is_verified': True,
                        'created_at': '2024-01-01T00:00:00Z',
                        'updated_at': '2024-01-01T00:00:00Z'
                    },
                    'is_new_user': False
                },
                response_only=True
            )
        ]
    )
    def post(self, request):
        serializer = OTPLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        otp = serializer.validated_data['otp']
        
        # Verify OTP and get phone number
        otp_data = redis_service.verify_otp(otp)
        if not otp_data:
            return Response(
                {'error': 'Invalid or expired OTP code'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        phone_number = otp_data.get('phone_number')
        
        # Get user data from Redis
        user_data = redis_service.get_user_data(phone_number)
        if not user_data:
            return Response(
                {'error': 'User data not found. Please try again.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user exists in database
        try:
            user = User.objects.get(phone_number=phone_number)
            is_new_user = False
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create(
                phone_number=phone_number,
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                tg_user_id=user_data.get('tg_user_id'),
                is_verified=True  # OTP verification means user is verified
            )
            is_new_user = True
        
        # Generate tokens
        token = JWTTokenGenerator.generate_token(user)
        refresh_token = JWTTokenGenerator.generate_refresh_token(user)
        
        # Clean up Redis data
        redis_service.delete_user_data(phone_number)
        
        response_data = {
            'access_token': token,
            'refresh_token': refresh_token,
            'user': {
                'id': str(user.id),
                'phone_number': user.phone_number,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'is_verified': user.is_verified,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
            },
            'is_new_user': is_new_user
        }
        
        response_serializer = OTPLoginResponseSerializer(response_data)
        return Response(response_serializer.data)


class RefreshTokenView(APIView):
    """
    Refresh JWT token endpoint
    """
    permission_classes = [AllowAny]
    serializer_class = RefreshTokenSerializer
    
    @extend_schema(
        operation_id='user_refresh_token',
        summary='Refresh JWT Token',
        description='Refresh expired JWT access token using refresh token',
        request=RefreshTokenSerializer,
        responses={
            200: RefreshResponseSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
        },
        examples=[
            OpenApiExample(
                'Refresh Token Request',
                summary='Refresh token request',
                description='Example refresh token request',
                value={
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                },
                request_only=True
            ),
            OpenApiExample(
                'Refresh Token Success Response',
                summary='Successful token refresh response',
                description='Response when token refresh is successful',
                value={
                    'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                },
                response_only=True
            )
        ]
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        refresh_token = serializer.validated_data['refresh_token']
        
        payload = JWTTokenGenerator.verify_token(refresh_token)
        
        if not payload or payload.get('type') != 'refresh':
            return Response(
                {'error': 'Invalid refresh token'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            user = User.objects.get(id=payload['user_id'])
            new_token = JWTTokenGenerator.generate_token(user)
            
            response_data = {
                'access_token': new_token,
            }
            
            response_serializer = RefreshResponseSerializer(response_data)
            return Response(response_serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )


class ProfileView(APIView):
    """
    Get current user profile
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    
    @extend_schema(
        operation_id='user_profile',
        summary='Get User Profile',
        description='Get current authenticated user profile information',
        responses={
            200: UserProfileSerializer,
            401: ErrorSerializer,
        },
        examples=[
            OpenApiExample(
                'Profile Success Response',
                summary='User profile response',
                description='Response with user profile information',
                value={
                    'id': '01HZ8X9K2M3N4P5Q6R7S8T9U0V',
                    'phone_number': '998931159963',
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john@example.com',
                    'is_verified': True,
                    'created_at': '2024-01-01T00:00:00Z',
                    'updated_at': '2024-01-01T00:00:00Z'
                },
                response_only=True
            )
        ]
    )
    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)


class LogoutView(APIView):
    """
    Logout endpoint (client-side token removal)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutResponseSerializer
    
    @extend_schema(
        operation_id='user_logout',
        summary='User Logout',
        description='Logout user (client-side token removal)',
        responses={
            200: LogoutResponseSerializer,
            401: ErrorSerializer,
        },
        examples=[
            OpenApiExample(
                'Logout Success Response',
                summary='Logout success response',
                description='Response when logout is successful',
                value={
                    'message': 'Successfully logged out'
                },
                response_only=True
            )
        ]
    )
    def post(self, request):
        serializer = LogoutResponseSerializer({'message': 'Successfully logged out'})
        return Response(serializer.data)


