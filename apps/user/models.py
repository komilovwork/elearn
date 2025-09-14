from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from base.models import BaseModel


class UserManager(BaseUserManager):
    """
    Custom user manager for phone number authentication
    """
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('The phone number must be set')
        
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractUser, BaseModel):
    """
    Custom User model with additional fields
    """

    username = None
    phone_number = models.CharField(max_length=20, unique=True)
    tg_user_id = models.BigIntegerField(null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    github_username = models.CharField(max_length=39, unique=True, blank=True, null=True)
    photo = models.CharField(max_length=1000, blank=True, null=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else self.phone_number

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.phone_number
