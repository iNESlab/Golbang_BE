'''
MVP demo ver 0.0.1
2024.06.19
golbang/accounts/managers.py
'''
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def create_user(self, username, email, password, full_name, phone_number, date_of_birth, **extra_fields):
        if not username:
            raise ValueError("User must have a username")
        if not email:
            raise ValueError("User must have an email")
        
        user = self.model(
            username = username,
            full_name = full_name,
            email = self.normalize_email(email),
            phone_number = phone_number,
            date_of_birth = date_of_birth,
            **extra_fields
        ) 
        user.set_password(password)
        user.save(using=self._db)

        return user

    # python manage.py createsuperuser 명령어 입력 시 해당 함수가 사용됨
    def create_superuser(self, username, full_name, email, phone_number, password, date_of_birth, **extra_fields):
        user = self.create_user(
            username = username,
            password = password,
            full_name = full_name,
            email = email,
            phone_number = phone_number,
            date_of_birth = date_of_birth,
            **extra_fields
        )

        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)

        return user
        # if extra_fields.get('is_staff') is not True:
        #     raise ValueError(_('Superuser must have is_staff=True.'))
        # if extra_fields.get('is_superuser') is not True:
        #     raise ValueError(_('Superuser must have is_superuser=True.'))
        # return self.create_user(email, password, **extra_fields)