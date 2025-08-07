# create_superuser.py
import os
import django
from django.contrib.auth import get_user_model

# Django 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'golbang.settings')
django.setup()

User = get_user_model()

def create_superuser(username, email, password):
    if User.objects.filter(email=email).exists():
        print('Superuser already exists')
    else:
        User.objects.create_superuser(user_id=username, email=email, password=password)
        print('Superuser created successfully')

if __name__ == '__main__':
    # 환경 변수에서 이메일, 사용자 ID, 비밀번호 가져오기
    email = os.getenv("DJANGO_SUPERUSER_EMAIL")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
    username = os.getenv("DJANGO_SUPERUSER_USERNAME")  # 기본 슈퍼유저 ID

    # 이메일과 비밀번호가 제공되었는지 확인
    if email and password and username:
        create_superuser(username, email, password)
    else:
        print("Environment variables DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD, and DJANGO_SUPERUSER_ID are required.")
