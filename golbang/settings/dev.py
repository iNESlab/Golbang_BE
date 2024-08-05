# golbang/settings/dev.py

from .base import *

BASE_DIR = Path(__file__).resolve().parent.parent

# 환경변수 설정
# Take environment variables from .env file
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, "../.env"))

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

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

CORS_ORIGIN_ALLOW_ALL = True  # 개발 중 모든 도메인 허용
