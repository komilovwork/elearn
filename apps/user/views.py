from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from apps.base.auth import JWTTokenGenerator
from apps.user.models import User
from apps.user.serializers import (
    LoginSerializer, RefreshTokenSerializer, UserProfileSerializer,
    LoginResponseSerializer, RefreshResponseSerializer, LogoutResponseSerializer,
    ErrorSerializer
)
from drf_spectacular.utils import extend_schema, OpenApiExample


class LoginView(APIView):
    """
    Login endpoint that returns JWT token
    """
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    @extend_schema(
        operation_id='user_login',
        summary='User Login',
        description='Authenticate user with phone number and password, returns JWT tokens',
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
        },
        examples=[
            OpenApiExample(
                'Login Request',
                summary='Login with phone number and password',
                description='Example login request',
                value={
                    'phone_number': '998931159963',
                    'password': 'your_password'
                },
                request_only=True
            ),
            OpenApiExample(
                'Login Success Response',
                summary='Successful login response',
                description='Response when login is successful',
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
                    }
                },
                response_only=True
            )
        ]
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']
        
        try:
            user = User.objects.get(phone_number=phone_number)
            if user.check_password(password):
                token = JWTTokenGenerator.generate_token(user)
                refresh_token = JWTTokenGenerator.generate_refresh_token(user)
                
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
                    }
                }
                
                response_serializer = LoginResponseSerializer(response_data)
                return Response(response_serializer.data)
            else:
                return Response(
                    {'error': 'Invalid credentials'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )


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
