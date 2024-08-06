# golbang/settings/prod.py
from .base import *

BASE_DIR = Path(__file__).resolve().parent.parent

# 환경변수 설정
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, "../.env.prod"))

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("MYSQL_DB_NAME"),
        "USER": env("MYSQL_DB_USER"),
        "PASSWORD": env("MYSQL_DB_PASSWORD"),
        "HOST": env("MYSQL_DB_HOST"),
        "PORT": env("MYSQL_DB_PORT"),
    }
}

DEBUG = False
ALLOWED_HOSTS = [
    env("MAIN_DOMAIN"),
    "43.202.23.152",
    # "web",  # Docker Compose 서비스 이름
    # "localhost",
    # "127.0.0.1"
]

CORS_ORIGIN_ALLOW_ALL = False
CORS_ORIGIN_WHITELIST = [
    "http://" + env("MAIN_DOMAIN"),
    "http://43.202.23.152",
    "http://localhost:8000",  # Docker 내부에서 접근할 수 있는 도메인
    "http://127.0.0.1:8000",
]  # 프로덕션 도메인만 허용

SECURE_SSL_REDIRECT = True  # SSL 사용 시 리디렉션
SECURE_HSTS_SECONDS = 31536000  # HTTP Strict Transport Security (HSTS)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# AWS_QUERYSTRING_AUTH = False  # URL에 인증 정보를 포함하지 않음
