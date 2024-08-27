'''
MVP demo ver 0.0.7
2024.08.27
accounts/urls.py

역할: accounts 앱 내의 URL API 엔드포인트 설정
현재 기능:
- 회원가입, 로그인, 로그아웃, 토큰재발급
- 소셜 로그인(구글, 카카오, 네이버)
- 회원정보 조회 및 수정, 비밀번호 변경
'''

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from accounts.social_login import google_callback, google_login, kakao_callback, kakao_login, naver_callback, naver_login
from .views import signup_first_step, signup_second_step, social_login, login_success, \
    PasswordManagementView, UserInfoViewSet
from auth.api import LoginApi, RefreshJWTToken, LogoutApi

# end point: api/user
router = DefaultRouter()
router.register(r'info', UserInfoViewSet, basename='user-info')  # 'users/info/'로 연결

urlpatterns = [
    # TODO: URL 패턴 분리 필요 (계정 / 소셜 로그인 / 회원정보)
    path('signup/step-1/', signup_first_step, name='signup_first_step'),    # 회원가입 - 1 엔드포인트
    path('signup/step-2/', signup_second_step, name='signup_second_step'),  # 회원가입 - 2 엔드포인트
    path('login/', LoginApi.as_view(), name='login'),                       # 로그인 엔드포인트
    path('logout/', LogoutApi.as_view(), name='logout'),                    # 로그아웃 엔드포인트
    path('refresh/', RefreshJWTToken.as_view(), name='refresh_token'),      # 토큰 갱신 엔드포인트

    # 소셜 로그인 관련 엔드포인트
    path('social-login/', social_login, name='social_login'),
    path('google-login/', google_login, name='google_login'),
    path('google-callback/', google_callback, name='google_callback'),
    path('naver-login/', naver_login, name='naver_login'),
    path('naver-callback/', naver_callback, name='naver_callback'),
    path('kakao-login/', kakao_login, name='kakao_login'),
    path('kakao-callback/', kakao_callback, name='kakao_callback'),
    path('login-success/', login_success, name='login_success'), # 소셜 로그인 성공 엔드포인트

    # 회원정보 조회 및 수정 엔드포인트
    path('', include(router.urls)),  # 'users/info/'로 접근 가능  # 회원정보 조회 및 수정
    path('info/password/verify/', PasswordManagementView.as_view(), {'action': 'verify'}, name='password-verify'), # 비밀번호 인증
    path('info/password/change/', PasswordManagementView.as_view(), {'action': 'change'}, name='password-change'), # 비밀번호 수정
]
