'''
MVP demo ver 0.0.1
2024.06.19
golbang/accounts/models.py
'''

from datetime import date
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

from .managers import UserManager

# Custom User 
class User(AbstractUser):
    # UUID 기본키. 새로운 사용자가 생성될 때마다 고유한 UUID 자동 할당
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  
    
    username = models.CharField("사용자 아이디", unique=True, max_length=150, default='unknown_user') # 개인 user Id
    password = models.CharField("비밀번호", max_length=128)

    full_name = models.CharField("이름", max_length=128, default='Unknown')
    
    email = models.EmailField("이메일주소", unique=True)
    login_type = models.CharField(max_length=10, choices=[('general', 'General'), ('social', 'Social')], default='general')
    provider = models.CharField(max_length=50, null=True, blank=True)
    
    phone_number = models.CharField("전화번호", max_length=20, default="000-000-0000")
    address = models.CharField("거주지 주소", max_length=255, null=True, blank=True)
    date_of_birth = models.DateField("생일", default=date.today)
    handicap = models.CharField("핸디캡 정보", max_length=20, default='N/A')
    student_id = models.CharField("학번", max_length=50, null=True, blank=True)
    
    created_at = models.DateTimeField("가입일", auto_now_add=True)
    updated_at = models.DateTimeField("계정 수정일", auto_now=True)
    last_login = models.DateTimeField("최근 접속일", auto_now=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'username' 
    REQUIRED_FIELDS = ['full_name', 'phone_number', 'email', 'address', 'date_of_birth']

    objects = UserManager()

    # 객체를 문자열로 표현하는 함수
    def __str__(self):
        return f"{self.username} / {self.email} / {self.full_name}"
        # e.g. "minbory925 / minbory925@email.com / Minjeong"

    # 사용자가 특정 권한을 가지고 있는지 여부를 결정
    def has_perm(self, perm, obj=None):
        return True
    
    # 사용자가 특정 애플리케이션 내의 모든 권한을 가지고 있는지 여부를 결정
    def has_module(self, app_label):
        return True
    
    class Meta:
        db_table = 'auth_user'