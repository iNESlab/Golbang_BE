'''
MVP demo ver 0.0.5
2024.07.27
golbang/settings.py
'''

from datetime import timedelta
import os
import environ
import pymysql
import redis
import urllib.parse as urlparse
import firebase_admin                   # FCM
from firebase_admin import credentials  # FCM

# 로컬에서 테스트를 원할 시, 아래 두 줄의 주석을 해제하면 됨 (깃허브에 올릴 떄는 주석처리 하기!)
from pathlib import Path

from celery.schedules import crontab

pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 환경변수 설정
# Take environment variables from .env file
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY') # 환경변수를 사용할 파일
REFRESH_TOKEN_SECRET = env('REFRESH_TOKEN_SECRET') 

MAIN_DOMAIN = env('MAIN_DOMAIN')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True # 프로덕션 환경에서는 False로 해야 함

ALLOWED_HOSTS = [
    'localhost', 
    '10.0.2.2',
    '.golf-bang.store', 
    '10.0.1.27',
    '127.0.0.1',
    '52.79.60.77',
    '43.201.74.202',
    env('ALB_DOMAIN')# ALB 도메인
] 

# FCM
cred_path = os.path.join(BASE_DIR, "serviceAccountKey.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

# AWS
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')

# S3 Storages
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_FILE_OVERWRITE = False   # 같은 이름을 가진 파일이 업로드되었을 때 덮어쓸 것인가?
AWS_QUERYSTRING_AUTH = True     # URL로 액세스 키가 넘어가게 할 것인가?

# 퍼블릭 읽기 권한 설정 제거
# AWS_DEFAULT_ACL = 'public-read' # 이 설정은 기본적으로 모든 파일을 퍼블릭 읽기 가능으로 설정함. 필요에 따라 활성화하기

# S3를 이용한 정적 파일 및 미디어 파일 설정
AWS_LOCATION = 'static'
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# 이메일
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # 예: Gmail
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'iamgolbang@gmail.com'  # 이메일 계정
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')  # 이메일 비밀번호 또는 앱 비밀번호
DEFAULT_FROM_EMAIL = 'iamgolbang@gmail.com' # 이메일이 발송될 때 수신자가 보게 되는 발신자 이메일 주소

# OPEN AI API KEY
OPENAI_API_KEY = env('OPENAI_API_KEY')

# 중복된 STATIC_URL 제거
# Static files (CSS, JavaScript, Images)
# STATIC_URL = '/static/' # 이 부분은 S3를 사용하지 않을 경우에만 활성화
# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
# 로컬 개발용 MEDIA 설정 (라디오 임시 파일용)
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# LOCAL_MEDIA_URL = '/media/'

# Application definition
INSTALLED_APPS = [
    # ==========
    # 비동기 통신
    # ==========
    'channels',
    'daphne',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # ==========
    # 애플리케이션
    # ==========
    'accounts',
    'clubs',
    'events',
    'participants',
    'golf_data',
    'notifications',
    'feedbacks',
    'calculator',
    'chat',  # 🔧 채팅 앱
    # 'broadcast',  # 🔧 추가: 방송 앱

    # ==========
    # DRF (Django Rest Framework)
    # - REST API 엔드포인트를 위해 필요하다.
    # ==========
    'rest_framework',
    #'rest_framework_simplejwt',
    #'rest_framework_simplejwt.token_blacklist', # 로그아웃을 위한 블랙리스트

    # ==========
    # OAUTH (drf-social-oauth2)
    # - 이메일 비밀번호 및 구글과 페이스북과 같이 소셜로그인을 위한 oauth2 토큰 기반 인증을 가능하게 합
    # ==========
    'oauth2_provider',
    'social_django', # Python social auth django app
    'drf_social_oauth2',

    # ==========
    # Other..
    # ==========
    'corsheaders',  # Cross-Origin Resource Sharing (CORS)
    'drf_yasg',     # Swagger
    'storages',     # Amazon S3 (django-storages)
]
# 웹 소켓을 위한 비동기 애플리케이션
ASGI_APPLICATION = 'golbang.asgi.application'
REDIS_PASSWORD = os.environ.get('MYSQL_DB_PASSWORD','')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts":[f"redis://:{os.environ.get('MYSQL_DB_PASSWORD')}@redis:6379/0"],
        },
    },
}

# Celery
CELERY_BROKER_URL = f'redis://:{REDIS_PASSWORD}@redis:6379/0'
CELERY_RESULT_BACKEND = f'redis://:{REDIS_PASSWORD}@redis:6379/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_BEAT_SCHEDULE = {
    'update-club-rankings-every-day': {
        'task': 'clubs.tasks.calculate_club_ranks_and_points',
        'schedule': crontab(minute=0, hour=0),  # 매일 자정에 실행
    },
}
# settings.py (테스트 환경에서만 사용)
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True



AUTH_USER_MODEL = 'accounts.User' # Custom User Model


# REST framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',  # 인증된 요청인지 확인
        'rest_framework.permissions.IsAdminUser',  # 관리자만 접근 가능
        'rest_framework.permissions.AllowAny',  # 누구나 접근 가능
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT를 통한 인증방식 사용
        #drf-social-oauth2
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',  # django-oauth-toolkit >= 1.0.0
        'drf_social_oauth2.authentication.SocialAuthentication',
    ),
    'EXCEPTION_HANDLER': 'utils.error_handlers.custom_exception_handler', # 커스텀 예외처리
    'DEFAULT_PARSER_CLASSES': ( # 파싱
            'rest_framework.parsers.JSONParser',
            'rest_framework.parsers.MultiPartParser',
            'rest_framework.parsers.FormParser',
    ),
}

# JWT 관련 설정
#REST_USE_JWT = True

SIMPLE_JWT = {
    'SIGNING_KEY': SECRET_KEY,
    'ACCESS_TOKEN_LIFETIME': timedelta(weeks=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(weeks=3),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',  # 사용자 모델에서 ID 필드 지정
    'USER_ID_CLAIM': 'user_id',  # 토큰 내부에서 사용자 ID를 저장할 키 #TODO: user_id -> account_id
}

# TODO: 추후 settings.dev, settgins.prod로 파일 분리가 필요함
CSRF_TRUSTED_ORIGINS = [
    'https://us.golf-bang.store',
    'https://dev.golf-bang.store',
    'https://us.golf-bang.store:8000',
    'https://dev.golf-bang.store:8000',
    'http://10.0.2.2:8080',  # Flutter 개발 환경
]

# CSRF 설정
CSRF_COOKIE_NAME = 'csrftoken'
# CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'

# 실제 운영 환경에서는 아래와 같이 특정 도메인만 허용하도록 설정해야 합니다.
CORS_ORIGIN_ALLOW_ALL = False  # 모든 도메인 허용 비활성화
CORS_ORIGIN_WHITELIST = [
    'https://us.golf-bang.store',
    'https://dev.golf-bang.store',
    'http://10.0.2.2:8080', # Flutter 개발 환경
]

CORS_ALLOW_CREDENTIALS = True

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware', # 개발 환경에서 CSRF 검사 비활성화 / 아래의 이유
        # RESTful API: REST API는 일반적으로 상태가 없고 세션을 사용하지 않으며, 토큰 기반 인증(예: JWT)을 많이 사용한다. 이 경우 CSRF 공격의 위험이 줄어든다. 따라서 이러한 API에서는 CSRF 보호를 비활성화하는 것이 일반적
        # 모바일 애플리케이션: 모바일 앱은 브라우저를 통해 작동하지 않으며, API 요청을 위해 자바스크립트를 실행하지 않는다. 따라서 CSRF 공격의 대상이 되지 않음.
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # CORS
    'corsheaders.middleware.CorsMiddleware',
]


ROOT_URLCONF = 'golbang.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # drf-social-oauth2
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

# 템플릿 경로
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

# django가 사용자 인증을 위해 사용할 백엔드 정의
AUTHENTICATION_BACKENDS = (
    # django
    'django.contrib.auth.backends.ModelBackend',    # 기본 Django 인증 백엔드 (세션 기반 인증 시스템)
    'auth.authenticate.EmailorUsernameAuthBackend', # 사용자 정의 인증 백엔드 (직접 정의 / 이메일 or 사용자 아이디를 사용해서 인증)
    # drf-social-oauth2
    'drf_social_oauth2.backends.DjangoOAuth2',      # 소셜 로그인 인증 백엔드
    # Social Oauth2
    'social_core.backends.google.GoogleOAuth2',     # 구글 소셜 로그인 백엔드 추가
    'social_core.backends.naver.NaverOAuth2',       # 네이버 소셜 로그인 백엔드 추가
    'social_core.backends.kakao.KakaoOAuth2',       # 카카오 소셜 로그인 백엔드 추가
)
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

STATE = env('STATE')

GOOGLE_CALLBACK_URL = env('GOOGLE_CALLBACK_URL')
KAKAO_CALLBACK_URL = env('KAKAO_CALLBACK_URL')
NAVER_CALLBACK_URL = env('NAVER_CALLBACK_URL')

# Social Oauth2
## Google  Social Login 설정
SOCIAL_AUTH_GOOGLE_CLIENT_ID = env('SOCIAL_AUTH_GOOGLE_CLIENT_ID')
SOCIAL_AUTH_GOOGLE_SECRET = env('SOCIAL_AUTH_GOOGLE_SECRET')
SOCIAL_AUTH_GOOGLE_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

## Naver Social Login 설정
SOCIAL_AUTH_NAVER_CLIENT_ID = env('SOCIAL_AUTH_NAVER_CLIENT_ID')
SOCIAL_AUTH_NAVER_SECRET = env('SOCIAL_AUTH_NAVER_SECRET')
SOCIAL_AUTH_NAVER_SCOPE = [
    'email',
    'name',
    'nickname',
    'birthday',
]

## Kakao Social Login 설정
SOCIAL_AUTH_KAKAO_CLIENT_ID = env('SOCIAL_AUTH_KAKAO_CLIENT_ID')
SOCIAL_AUTH_KAKAO_SECRET = env('SOCIAL_AUTH_KAKAO_SECRET')
SOCIAL_AUTH_KAKAO_SCOPE = [
    'account_email',
    'profile_nickname',
]

# Apple Sign-In 설정
SOCIAL_AUTH_APPLE_CLIENT_ID = env('SOCIAL_AUTH_APPLE_CLIENT_ID', default='')  # Bundle ID
SOCIAL_AUTH_APPLE_TEAM_ID = env('SOCIAL_AUTH_APPLE_TEAM_ID', default='')
SOCIAL_AUTH_APPLE_KEY_ID = env('SOCIAL_AUTH_APPLE_KEY_ID', default='')
SOCIAL_AUTH_APPLE_PRIVATE_KEY = env('SOCIAL_AUTH_APPLE_PRIVATE_KEY', default='')


# oauth2_settings.DEFAULTS['ACCESS_TOKEN_EXPIRE_SECONDS'] = 1.577e7

WSGI_APPLICATION = 'golbang.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('MYSQL_DB_NAME'),
        'USER': env('MYSQL_DB_USER'),
        'PASSWORD': env('MYSQL_DB_PASSWORD'),
        'HOST': env('MYSQL_DB_HOST'),
        'PORT': env('MYSQL_DB_PORT'),
        # 🔧 추가: 커넥션 풀 설정 (Max Connection 에러 방지)
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'autocommit': True,
        },
        'CONN_MAX_AGE': 0,        # 연결 재사용 안함 (WebSocket 환경에서 안전)
        'MAX_CONNS': 50,          # 최대 연결 수 제한 (기본값)
        'POOL_SIZE': 20,          # 커넥션 풀 크기 (기본값)
        'POOL_TIMEOUT': 30,       # 커넥션 대기 시간 (초)
        'POOL_RECYCLE': 3600,     # 커넥션 재활용 시간 (초)
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Logging
# DEBUG 레벨 이상의 메시지를 콘솔에 출력
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        # AWS SDK 로그 레벨 조정
        'boto3': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'botocore': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        's3transfer': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'urllib3': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'ko'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# https://hyun-am-coding.tistory.com/entry/Django-FCM-개발DRF
# DOCKER 사용시 FCM key 설정 방법

# service_account_key = {
#     "type": env("TYPE"),
#     "project_id": env("PROJECT_ID"),
#     "private_key_id": env("PRIVATE_KEY_ID"),
#     "private_key": env("PRIVATE_KEY").replace("\\\\n", "\\n"),
#     "client_email": env("CLIENT_EMAIL"),
#     "client_id": env("CLIENT_ID"),
#     "auth_uri": env("AUTH_URI"),
#     "token_uri": env("TOKEN_URI"),
#     "auth_provider_x509_cert_url": env("AUTH_PROVIDER_X509_CERT_URL"),
#     "client_x509_cert_url": env("CLIENT_X_509_CERT_URL"),
# }

# cred = credentials.Certificate(service_account_key)
# firebase_admin.initialize_app(cred)