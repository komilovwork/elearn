from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin configuration
    """
    list_display = ('phone_number', 'first_name', 'last_name', 'email', 'is_verified', 'is_staff', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'created_at', 'updated_at')
    search_fields = ('phone_number', 'first_name', 'last_name', 'email', 'github_username')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'birth_date', 'photo')}),
        ('Social', {'fields': ('tg_user_id', 'github_username')}),
        ('Permissions', {'fields': ('is_verified', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2'),
        }),
    )
