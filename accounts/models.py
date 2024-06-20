'''
MVP demo ver 0.0.1
2024.06.19
accounts/models.py
'''

from django.db import models
from django.contrib.auth.models import (BaseUserManager, AbstractBaseUser)

# 커스텀 유저 모델(Custom User Model)를 만들기 위해서는 두 클래스(BaseUserManager, AbstractBaseUser)를 구현해야 한다.

# BaseUserManager: 유저를 생성할 때 사용하는 헬퍼 클래스
# AbstractBaseUser: 실제 모델은 상속받아 생성
class UserManager(BaseUserManager):

    def create_user(self, email, userId, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not userId:
            raise ValueError('Users must have a user ID')
        
        email = self.normalize_email(email)
        user = self.model(email=email, userId=userId, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, userId, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, userId, password, **extra_fields)


class User(AbstractBaseUser):
    # step 1
    userId = models.CharField("사용자 아이디", unique=True, max_length=150, default='unknown_user')
    password = models.CharField("비밀번호", max_length=256)
    email = models.EmailField("이메일", unique=True)
    login_type = models.CharField(max_length=10, choices=[('general', 'General'), ('social', 'Social')], default='general')
    provider = models.CharField(max_length=50, null=True, blank=True)
    
    # step 2
    name = models.CharField("이름", max_length=128, default='Unknown')
    phone_number = models.CharField("전화번호", max_length=20, default='000-000-0000')
    address = models.CharField("주소", max_length=255, null=True, blank=True)
    date_of_birth = models.DateField("생일", null=True, blank=True)
    handicap = models.CharField("핸디캡", max_length=20, default='0')
    student_id = models.CharField("학번", max_length=50, null=True, blank=True)
    
    # auto
    created_at = models.DateTimeField("가입일", auto_now_add=True)
    updated_at = models.DateTimeField("계정 수정일", auto_now=True)
    last_login = models.DateTimeField("최근 접속일", auto_now=True)

    # manage
    is_admin = models.BooleanField(default=False) # 관리자
    is_active = models.BooleanField(default=True)

    objects = UserManager()  # 유저 매니저 설정

    USERNAME_FIELD = 'email'  # 로그인에 사용할 필드 설정
    REQUIRED_FIELDS = ['userId']  # 필수 필드 설정

    def __str__(self):
        return self.email

    # 사용자가 특정 권한을 가지고 있는지 여부를 결정
    def has_perm(self, perm, obj=None):
        return True # 권한 있음을 알림

    # 사용자가 특정 애플리케이션 내의 모든 권한을 가지고 있는지 여부를 결정
    def has_module_perms(self, app_label):
        return True # 주어진 앱의 모델에 접근 가능

    @property
    def is_staff(self):
        # True일 경우, django의 관리자 화면에 로그인할 수 있음
        return self.is_admin 