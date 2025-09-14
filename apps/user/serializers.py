from rest_framework import serializers
from .models import User


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, help_text="User's phone number")
    password = serializers.CharField(write_only=True, help_text="User's password")


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(help_text="Refresh token to get new access token")


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'first_name', 'last_name', 
            'email', 'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    user = UserProfileSerializer(help_text="User profile information")


class RefreshResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(help_text="New JWT access token")


class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="Logout success message")


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField(help_text="Error message")


class OTPLoginSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=6, help_text="6-digit OTP code")


class OTPLoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(help_text="JWT refresh token")
    user = UserProfileSerializer(help_text="User profile information")
    is_new_user = serializers.BooleanField(help_text="Whether this is a new user")
