# accounts/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from .managers import UserManager

# Custom User 
class User(AbstractUser):
    # UUID 기본키. 새로운 사용자가 생성될 때마다 고유한 UUID 자동 할당
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  
    
    username = models.CharField(max_length=150)
    email = models.EmailField(_('email address'), unique=True)
    login_type = models.CharField(max_length=10, choices=[('general', 'General'), ('social', 'Social')], default='general')
    provider = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    dob = models.DateField(_('date of birth'), null=True, blank=True)
    handicap = models.CharField(max_length=20, null=True, blank=True)
    student_id = models.CharField(max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def __str__(self):
        return self.email