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

from accounts.social_login import google_callback, google_login, mobile_google_login, integrate_google_account, mobile_apple_login, integrate_apple_account, check_user_id_availability, complete_social_registration
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
    path('google-login-mobile/', mobile_google_login, name='mobile_google_login'),  # 모바일용 구글 로그인
    path('integrate-google-account/', integrate_google_account, name='integrate_google_account'),  # Google 계정 통합
    path('apple-login-mobile/', mobile_apple_login, name='mobile_apple_login'),  # 모바일용 애플 로그인
    path('integrate-apple-account/', integrate_apple_account, name='integrate_apple_account'),  # Apple 계정 통합
    
    # 🔧 추가: 소셜 로그인 추가 정보 입력 관련
    path('check-user-id/', check_user_id_availability, name='check_user_id_availability'),  # 사용자 ID 중복 확인
    path('complete-social-registration/', complete_social_registration, name='complete_social_registration'),  # 소셜 로그인 회원가입 완료
    # path('naver-login/', naver_login, name='naver_login'),  # 사용하지 않음
    # path('naver-callback/', naver_callback, name='naver_callback'),  # 사용하지 않음
    # path('kakao-login/', kakao_login, name='kakao_login'),  # 사용하지 않음
    # path('kakao-callback/', kakao_callback, name='kakao_callback'),  # 사용하지 않음
    path('login-success/', login_success, name='login_success'), # 소셜 로그인 성공 엔드포인트

    # 회원정보 조회 및 수정 엔드포인트
    path('', include(router.urls)),  # 'users/info/'로 접근 가능  # 회원정보 조회 및 수정
    path('info/password/verify/', PasswordManagementView.as_view(), {'action': 'verify'}, name='password-verify'), # 비밀번호 인증
    path('info/password/change/', PasswordManagementView.as_view(), {'action': 'change'}, name='password-change'), # 비밀번호 수정
    path('info/password/forget/', PasswordManagementView.as_view(), {'action': 'forget'}, name='password-forget'), # 비밀번호 재발급
]
