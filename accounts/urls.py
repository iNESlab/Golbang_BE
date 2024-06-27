'''
MVP demo ver 0.0.1
2024.06.27
accounts/urls.py

역할: accounts 앱 내의 URL API 엔드포인트 설정
현재 기능:
- 회원가입, 로그인, 로그아웃
- 소셜 로그인(구글,)
'''

from django.urls import path
from accounts.social_login import google_callback, google_login, login_success
from .views import signup_first_step, signup_second_step, social_login
from auth.api import LoginApi, RefreshJWTToken, LogoutApi

# end point: api/user
urlpatterns = [
    path('signup/step-1/', signup_first_step, name='signup_first_step'),      # 회원가입 - 1 엔드포인트
    path('signup/step-2/', signup_second_step, name='signup_second_step'),    # 회원가입 - 2 엔드포인트
    path('login/', LoginApi.as_view(), name='login'),       # 로그인 엔드포인트
    path('logout/', LogoutApi.as_view(), name='logout'),    # 로그아웃 엔드포인트
    path('refresh/', RefreshJWTToken.as_view(), name='refresh_token'),  # 토큰 갱신 엔드포인트
    
    path('social-login/', social_login, name='social_login'),
    path('google-login/', google_login, name='google_login'),
    path('google-callback/', google_callback, name='google_callback'),
    path('login-success/', login_success, name='login_success'),

]   
