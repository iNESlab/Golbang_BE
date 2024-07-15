'''
MVP demo ver 0.0.2
2024.07.03
auth/authenticate.py

JWT 토큰을 사용한 사용자 인증 로직을 처리
- JWT 토큰 검증 
- 액세스 토큰 생성, 리프레시 토큰 생성
- 로그인 응답에 대한 JWT 토큰 설정
- 로그아웃 처리
- 토큰 만료 여부 확인
'''

import jwt
from rest_framework import exceptions           # DRF에서 제공하는 예외 클래스
from rest_framework.authentication import BaseAuthentication, CSRFCheck # DRF 기본 인증, CSRF 토큰 검사
from django.conf import settings                # django 설정 파일
from django.contrib.auth import get_user_model  # 현재 활성화된 사용자 모델
import datetime
from django.contrib.auth import backends
from django.db.models import Q

User = get_user_model()

'''
DRF의 인증 클래스와 함께 사용되어 요청의 JWT 토큰을 검증하는 클래스
'''
class EmailorUsernameAuthBackend(backends.ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None
        try:
            user = User.objects.get(
                Q(userId__exact=username) |  # userId 필드를 사용
                Q(email__exact=username)
            )
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class SafeJWTAuthentication(BaseAuthentication): # BaseAuthentication을 상속받아 JWT 인증 클래스를 정의
    # 요청(request)에서 인증 정보를 확인하는 함수
    def authenticate(self, request):
        authorization_header = request.headers.get('Authorization') # 요청 헤더에서 Authorization 값을 가져옴
        
        # Authorization 헤더가 없는 경우 None을 반환
        if not authorization_header:
            return None

        # 토큰 처리    
        try:
            # Authorization 헤더의 접두사를 추출 (bearer 토큰 가져오기 위함)
            prefix = authorization_header.split(' ')[0]
            if prefix.lower() != 'bearer':
                raise exceptions.AuthenticationFailed('Token is not Bearer')

            access_token = authorization_header.split(' ')[1] # Authorization 헤더에서 토큰 값을 추출

            # JWT 토큰을 디코딩하여 페이로드(payload)를 가져옴
            payload = jwt.decode(
                access_token, settings.SECRET_KEY, algorithms=['HS256']
            )
        # 예외처리
        except jwt.ExpiredSignatureError: # 토큰 만료된 경우
            raise exceptions.AuthenticationFailed('access_token expired')
        except IndexError: # 토큰 형식이 잘못된 경우
            raise exceptions.AuthenticationFailed('Token prefix missing')
        
        # 디코딩된 페이로드에서 사용자 ID를 사용하여 인증 자격을 확인
        return self.authenticate_credentials(request, payload['user_id'])
    
    # 사용자 자격을 확인하는 함수
    def authenticate_credentials(self, request, key):
        # 주어진 ID로 사용자를 조회
        user = User.objects.filter(id=key).first()
        
        # 예외처리
        if user is None: # 사용자가 없는 경우 인증 실패 예외처리
            raise exceptions.AuthenticationFailed('User not found')
        
        if not user.is_active: # 사용자가 비활서오하된 경우 실패 예외처리
            raise exceptions.AuthenticationFailed('User is inactive')
        
        # CSRF 검사 실행
        self.enforce_csrf(request)
        return (user, None)

    # CSRF 검사 처리 함수
    def enforce_csrf(self, request):
        check = CSRFCheck() # CSRF 검사 객체 생성
        
        check.process_request(request) # 요청에 대한 CSRF 검사 실행
        reason = check.process_view(request, None, (), {}) # 뷰에 대한 CSRF 검사를 실행
        # CSRF 검사 실패할 경우 예외처리 발생
        if reason: 
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')

'''
JWT 토큰 생성 함수
'''
# 액세스 토큰 생성 함수
def generate_access_token(user):
    # 액세스 토큰의 페이로드를 정의
    access_token_payload = {
        'user_id': user.id,
        'token_type': 'access',
        'exp': datetime.datetime.utcnow() + settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        'iat': datetime.datetime.utcnow(),
    }
    
    # JWT 토큰을 생성
    access_token = jwt.encode(
        access_token_payload,
        settings.SECRET_KEY, 
        algorithm='HS256'
    )
    
    return access_token # 생성된 액세스 토큰 반환

# 리프레시 토큰 생성 함수
def generate_refresh_token(user):
    # 리프레시 토큰의 페이로드를 정의
    refresh_token_payload = {
        'user_id': user.id,
        'token_type': 'refresh',
        'exp': datetime.datetime.utcnow() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
        'iat': datetime.datetime.utcnow(),
    }
    
    # JWT 리프레시 토큰을 생성
    refresh_token = jwt.encode(
        refresh_token_payload,
        settings.REFRESH_TOKEN_SECRET, 
        algorithm='HS256'
    )
    
    return refresh_token # 생성된 리프레시 토큰 반환

# 로그인 후 응답에 JWT 토큰을 설정하는 함수
def jwt_login(response, user):
    access_token = generate_access_token(user)      # 액세스 토큰 생성
    refresh_token = None

    # 액세스 토큰이 만료될 경우에만 리프레시 토큰 생성
    if is_token_expired(access_token):
        refresh_token = generate_refresh_token(user) # 리프레시 토큰 생성
    
    # 응답 객체에 데이터
    data = {
        'access_token': access_token,
    }
    
    if refresh_token:
        data['refresh_token'] = refresh_token
        response.set_cookie(key="refreshtoken", value=refresh_token, httponly=True) # 리프레시 토큰을 HTTP 전용 쿠키로 설정
    
    response.data = data
    
    return response # 응답 객체 반환

# 토큰 만료 확인 함수
def is_token_expired(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        exp = datetime.datetime.fromtimestamp(payload['exp'])
        return exp < datetime.datetime.utcnow()
    except jwt.ExpiredSignatureError:
        return True
    except Exception:
        return False