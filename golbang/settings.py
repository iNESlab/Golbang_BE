"""
Django settings for golbang project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
'''
MVP demo ver 0.0.3
2024.06.27
golbang/settings.py
'''

from datetime import timedelta
import os
import environ
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY') # 환경변수를 사용할 파일
REFRESH_TOKEN_SECRET = env('REFRESH_TOKEN_SECRET') 

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
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

    # ==========
    # DRF (Django Rest Framework)
    # - REST API 엔드포인트를 위해 필요하다.
    # ==========
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist', # 로그아웃을 위한 블랙리스트

    # ==========
    # OAUTH (drf-social-oauth2)
    # - 이메일 비밀번호 및 구글과 페이스북과 같이 소셜로그인을 위한 oauth2 토큰 기반 인증을 가능하게 합
    # ==========
    'oauth2_provider',
    'social_django', # Python social auth django app
    'drf_social_oauth2',
    
]

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
}

# JWT 관련 설정
REST_USE_JWT = True

SIMPLE_JWT = {
    'SIGNING_KEY': SECRET_KEY,
    'ACCESS_TOKEN_LIFETIME': timedelta(days=0, minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
}

# 아래는 필요 없음
# 일단 주석처리
# CSRF_TRUSTED_ORIGINS = [
#     'http://localhost:8000',  # 클라이언트의 도메인 추가
# ]

# CORS_ORIGIN_WHITELIST = [
#     'http://localhost:8000',  # 클라이언트의 도메인 추가
# ]

# # CSRF 설정
# CSRF_COOKIE_NAME = 'csrftoken'
# CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
# Social Oauth2
## Google  Social Login 설정
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env('SOCIAL_AUTH_GOOGLE_CLIENT_ID') 
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env('SOCIAL_AUTH_GOOGLE_SECRET')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

## Naver Social Login 설정
SOCIAL_AUTH_NAVER_KEY = env('SOCIAL_AUTH_NAVER_CLIENT_ID')
SOCIAL_AUTH_NAVER_SECRET = env('SOCIAL_AUTH_NAVER_SECRET')
SOCIAL_AUTH_NAVER_SCOPE = [
    'email',
    'name',
    'nickname',
    'birthday',
]

# KAKAO 소셜 로그인 설정
SOCIAL_AUTH_KAKAO_KEY = env('SOCIAL_AUTH_KAKAO_KEY')
SOCIAL_AUTH_KAKAO_SECRET = env('SOCIAL_AUTH_KAKAO_SECRET')
SOCIAL_AUTH_KAKAO_SCOPE = [
    'account_email',
    'profile_nickname',
]


# oauth2_settings.DEFAULTS['ACCESS_TOKEN_EXPIRE_SECONDS'] = 1.577e7

WSGI_APPLICATION = 'golbang.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
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


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'ko'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
