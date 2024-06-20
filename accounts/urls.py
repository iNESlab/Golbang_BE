'''
MVP demo ver 0.0.1
2024.06.19
accounts/urls.py

역할: accounts 앱 내의 URL API 엔드포인트 설정
현재 기능:
- 회원가입, 로그인, 로그아웃
'''

from django.urls import path
from auth.api import LoginApi, RefreshJWTToken, LogoutApi
from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),           # 회원가입 엔드포인트
    # path('login/', views.login, name='login'),       # 로그인 엔드포인트
    # path('logout/', views.logout, name='logout'),    # 로그아웃 엔드포인트
    path('login/', LoginApi.as_view(), name='login'),       # 로그인 엔드포인트
    path('logout/', LogoutApi.as_view(), name='logout'),    # 로그아웃 엔드포인트
    path('refresh/', RefreshJWTToken.as_view(), name='refresh_token'),  # 토큰 갱신 엔드포인트
]
