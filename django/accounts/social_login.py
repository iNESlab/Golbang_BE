'''
MVP demo ver 0.0.3
2024.06.28
accounts/social_login.py

역할: 사용자가 소셜 로그인 시, 사용자 정보를 처리하는 view
- 코드 가독성과 유지보수성을 높이기 위해 views.py로부터 파일을 분리

기능:
1. 구글, 애플 소셜 로그인 (카카오, 네이버는 제거됨)
2. 공통된 기능은 헬퍼 함수 처리
- create_user_and_login: 새로운 사용자를 생성하고 JWT 토큰을 반환.
- get_access_token: 주어진 토큰 URL과 데이터로 액세스 토큰을 가져옴.
3. 소셜 로그인 함수 구조 통일하여 가독성, 유지보수성, 일관성 향상
- 각 소셜 로그인 함수에서 공통적인 패턴을 따름.
- 액세스 토큰을 가져오는 과정과 사용자 정보를 가져오는 과정을 통일성 있게 처리.

'''
from django.conf import settings
from django.urls import reverse
import requests
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from json import JSONDecodeError
from rest_framework_simplejwt.tokens import RefreshToken  # SIMPLE_JWT 토큰 생성
import uuid  # UUID 생성을 위한 import

User = get_user_model()

def create_user_and_login(response, email, user_id, name, provider, fcm_token=None):
    """
    새로운 사용자를 생성하고 JWT 토큰을 반환하는 헬퍼 함수
    """
    password = User.objects.make_random_password()  # 소셜 로그인이기 때문에 비밀번호는 랜덤하게 생성
    user = User.objects.create(
        email=email,
        user_id=user_id,
        name=name,
        login_type='social',
        provider=provider,
        password=password,
        fcm_token=fcm_token  # 🔧 추가: FCM 토큰 저장
    )
    user.save() # user 저장
    
    # SIMPLE_JWT를 사용하여 토큰 생성
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    
    # 모바일 앱용 응답 데이터 설정
    response.data = {
        'status': status.HTTP_201_CREATED,
        'message': 'User created successfully',
        'data': {
            'access_token': access_token,
            'refresh_token': str(refresh),
            'user_exists': False,
            'new_user_id': user.user_id,
            'new_user_name': user.name,
        }
    }
    
    # 리프레시 토큰을 쿠키에 설정 (웹용)
    response.set_cookie(
        key="refreshtoken",
        value=str(refresh),
        httponly=True,
        secure=True,
        samesite="None",
    )

    return response

def get_access_token(token_url, token_data):
    """
    주어진 토큰 URL과 데이터로 액세스 토큰을 가져오는 헬퍼 함수
    """
    token_response      = requests.post(token_url, data=token_data)
    token_response_json = token_response.json()
    access_token        = token_response_json.get('access_token') # 액세스 토큰을 응답에서 가져옴

    # 액세스 토큰이 없는 경우 예외 처리
    if not access_token:
        error = token_response_json.get("error", "No access token in response")
        raise JSONDecodeError(error)

    return access_token

###############
# 구글 로그인
###############
@api_view(['GET'])
@permission_classes([AllowAny])
def google_login(request):
    """
    구글 로그인 URL로 리디렉션
    """
    google_client_id = settings.SOCIAL_AUTH_GOOGLE_CLIENT_ID
    # 클라이언트 애플리케이션은 사 사용자를 해당 소셜 로그인 제공자(구글, 네이버, 카카오)의 인증 페이지로 리디렉션한다.
    redirect_uri = settings.GOOGLE_CALLBACK_URL
    # 사용자가 로그인하고 인증을 완료하면, 소셜 로그인 제공자는 사전에 등록된 콜백 URL로 사용자를 다시 리디렉션한다.
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?response_type=code"
        f"&client_id={google_client_id}&redirect_uri={redirect_uri}"
        f"&scope=openid%20email%20profile"
    )
    return redirect(google_auth_url) # 구글 로그인 페이지로 리디렉션
    #return JsonResponse({"auth_url": google_auth_url})

@api_view(['GET'])
@permission_classes([AllowAny])
def google_callback(request):
    """
    구글 OAuth2 콜백 처리
    """
    try:
        code = request.GET.get('code') # 구글에서 반환된 인증 코드 추출
        if not code: # 코드가 없으면 로그인 페이지로 리디렉션
            return redirect('google_login')

        # 인증 코드를 사용하여 소셜 로그인 제공자에게 액세스 토큰을 요청
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.SOCIAL_AUTH_GOOGLE_CLIENT_ID,
            "client_secret": settings.SOCIAL_AUTH_GOOGLE_SECRET,
            "redirect_uri": request.build_absolute_uri(reverse('google_callback')),
            "grant_type": "authorization_code",
        }
        access_token = get_access_token(token_url, token_data)
        
        # user_info_url: 소셜 로그인에서 액세스 토큰을 사용하여 사용자 정보를 가져오는 역할
        # 액세스 토큰을 사용하여 사용자 정보를 가져온다.
        user_info_url       = "https://www.googleapis.com/oauth2/v3/userinfo"
        user_info_response  = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
        user_info           = user_info_response.json()

        # CHECK SUCCESSFULLY LOGIN PROCESS
        print("===GOOGLE LOGIN USER===", user_info)

        email   = user_info.get("email")
        name    = user_info.get("name", "Unknown") # 이름이 없으면 "Unknown"으로 설정

        # 이메일이 없으면 로그인 페이지로 리디렉션
        if not email:
            return redirect('google_login')

        try: # 기존 사용자인지 확인
            user = User.objects.get(email=email)
        except User.DoesNotExist:  # 사용자 정보가 없으면 회원가입 진행
            # 🔧 수정: 신규 사용자는 임시 ID로 생성하고 추가 정보 입력 페이지로 리다이렉트
            import uuid
            temp_user_id = f"temp_{str(uuid.uuid4())[:8]}_google"
            
            # 임시 사용자 생성 (추가 정보 입력 완료 후 실제 ID로 업데이트)
            temp_user = User.objects.create(
                user_id=temp_user_id,
                email=email,
                name=name,
                provider='google',
                fcm_token=fcm_token,
                is_active=True
            )
            
            return Response({
                'status': status.HTTP_226_IM_USED,  # 226: 추가 정보 입력 필요
                'message': '추가 정보 입력이 필요합니다',
                'data': {
                    'temp_user_id': temp_user_id,
                    'email': email,
                    'display_name': name,
                    'provider': 'google',
                    'requires_additional_info': True
                }
            }, status=status.HTTP_226_IM_USED)

        response = Response(status=status.HTTP_200_OK)
        
        # SIMPLE_JWT를 사용하여 토큰 생성
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # 응답 데이터 설정
        response.data = {
            'access_token': access_token,
        }
        
        # 리프레시 토큰을 쿠키에 설정
        response.set_cookie(
            key="refreshtoken",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="None",
        )
        
        return response
    
    except Exception as e:
        return JsonResponse({
            "error": str(e),
        }, status=status.HTTP_404_NOT_FOUND)
    
###############
# 네이버 로그인 (사용하지 않음 - 주석 처리)
###############
# @api_view(['GET'])
# @permission_classes([AllowAny])
# def naver_login(request):
#     """
#     네이버 로그인 URL로 리디렉션
#     """
#     # ... (전체 함수 내용 주석 처리)

# @api_view(['GET'])
# @permission_classes([AllowAny])
# def naver_callback(request):
#     """
#     네이버 OAuth2 콜백 처리
#     """
#     # ... (전체 함수 내용 주석 처리)

###############
# 카카오 로그인 (사용하지 않음 - 주석 처리)
###############
# @api_view(['GET'])
# @permission_classes([AllowAny])
# def kakao_login(request):
#     """
#     카카오 로그인 URL로 리디렉션
#     """
#     # ... (전체 함수 내용 주석 처리)

# @api_view(['GET'])
# @permission_classes([AllowAny])
# def kakao_callback(request):
#     """
#     카카오 OAuth2 콜백 처리
#     """
#     # ... (전체 함수 내용 주석 처리)

###############
# 모바일 앱용 구글 로그인
###############
@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_google_login(request):
    """
    Flutter 앱에서 호출하는 구글 로그인 API
    구글 ID 토큰을 검증하고 JWT 토큰을 반환
    """
    try:
        # Flutter 앱에서 전송한 데이터
        id_token = request.data.get('id_token')
        access_token = request.data.get('access_token')
        email = request.data.get('email')
        display_name = request.data.get('display_name', 'Unknown')
        fcm_token = request.data.get('fcm_token')  # 🔧 추가: FCM 토큰
        
        if not id_token or not email:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'id_token and email are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 구글 ID 토큰 검증 (간단한 검증)
        # TODO: 실제 운영환경에서는 구글 공개키로 토큰 서명 검증 필요
        
        try:
            # 기존 사용자인지 확인
            user = User.objects.get(email=email)
            
            # 🔧 수정: 이미 Google 계정과 통합된 사용자인지 확인
            if user.provider == 'google' or user.login_type == 'hybrid':
                # 이미 통합된 계정이면 바로 로그인 처리
                
                # 🔧 추가: FCM 토큰 업데이트 (다를 때만)
                if fcm_token and user.fcm_token != fcm_token:
                    user.fcm_token = fcm_token
                    user.save(update_fields=['fcm_token'])
                
                response = Response(status=status.HTTP_200_OK)
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                
                response.data = {
                    'status': status.HTTP_200_OK,
                    'message': 'Login successful',
                    'data': {
                        'access_token': access_token,
                        'refresh_token': str(refresh),
                        'user_exists': True,  # 🔧 수정: 기존 사용자임을 명시
                        'user_id': user.user_id,
                        'user_name': user.name,
                        'login_type': user.login_type,
                        'provider': user.provider,
                        'is_already_integrated': True,  # 이미 통합됨 표시
                    }
                }
                
                # 리프레시 토큰을 쿠키에 설정
                response.set_cookie(
                    key="refreshtoken",
                    value=str(refresh),
                    httponly=True,
                    secure=True,
                    samesite="None",
                )
                
                return response
            else:
                # 아직 통합되지 않은 계정이면 통합 옵션 제공
                return Response({
                    'status': status.HTTP_200_OK,
                    'message': 'User already exists',
                    'data': {
                        'user_exists': True,
                        'existing_user_id': user.user_id,
                        'existing_user_name': user.name or 'Unknown',
                        'login_type': user.login_type or 'general',
                        'provider': user.provider or 'none',
                        'needs_integration': True,  # 통합 필요 표시
                    }
                }, content_type='application/json; charset=utf-8')
            
        except User.DoesNotExist:
            # 새로운 사용자라면 임시 사용자 생성 후 226 응답
            import uuid
            unique_suffix = str(uuid.uuid4())[:8]  # UUID 앞 8자리만 사용
            temp_user_id = f"temp_{unique_suffix}_google"
            
            # 임시 사용자 생성
            temp_user = User.objects.create(
                email=email,
                user_id=temp_user_id,
                name=display_name,
                login_type='social',
                provider='google',
                password=User.objects.make_random_password(),
                fcm_token=fcm_token
            )
            temp_user.save()
            
            return Response({
                'status': status.HTTP_226_IM_USED,  # 226: 추가 정보 입력 필요
                'message': '추가 정보 입력이 필요합니다',
                'data': {
                    'temp_user_id': temp_user_id,
                    'email': email,
                    'display_name': display_name,
                    'provider': 'google',
                    'requires_additional_info': True
                }
            }, status=status.HTTP_226_IM_USED)
            
    except Exception as e:
        return Response({
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def integrate_google_account(request):
    """
    기존 계정을 Google 계정과 통합하는 API
    """
    try:
        email = request.data.get('email')
        id_token = request.data.get('id_token')
        display_name = request.data.get('display_name')
        
        if not email or not id_token:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'email and id_token are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 기존 사용자 찾기
            user = User.objects.get(email=email)
            
            # Google 계정 정보로 업데이트 (하이브리드 로그인 지원)
            user.login_type = 'hybrid'  # 일반 로그인 + 소셜 로그인 모두 지원
            user.provider = 'google'
            if display_name and not user.name:
                user.name = display_name
            user.save()
            
            print(f"✅ 계정 통합 완료: {user.email} -> provider: {user.provider}, login_type: {user.login_type}")
            
            # JWT 토큰 생성하여 반환
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            return Response({
                'status': status.HTTP_200_OK,
                'message': 'Account integration successful',
                'data': {
                    'access_token': access_token,
                    'refresh_token': str(refresh),
                    'user_exists': False,  # 통합 완료
                    'integrated_user_id': user.user_id,
                    'integrated_user_name': user.name,
                }
            }, content_type='application/json; charset=utf-8')
            
        except User.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

###############
# 애플 로그인
###############
import jwt
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def get_apple_public_keys():
    """
    애플 공개키 가져오기
    """
    try:
        response = requests.get('https://appleid.apple.com/auth/keys')
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"애플 공개키 가져오기 실패: {e}")
        raise Exception(f"애플 공개키 가져오기 실패: {e}")

def verify_apple_id_token(identity_token, client_id):
    """
    애플 ID 토큰 검증
    """
    try:
        # 1. 애플 공개키 가져오기
        apple_public_keys = get_apple_public_keys()
        
        # 2. 토큰 헤더에서 kid 추출
        unverified_header = jwt.get_unverified_header(identity_token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise Exception("토큰 헤더에서 kid를 찾을 수 없습니다")
        
        # 3. 해당 kid의 공개키 찾기
        public_key = None
        for key in apple_public_keys['keys']:
            if key['kid'] == kid:
                public_key = key
                break
        
        if not public_key:
            raise Exception("애플 공개키를 찾을 수 없습니다")
        
        # 4. 공개키를 PEM 형식으로 변환
        import base64
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        # JWK를 RSA 공개키로 변환
        n = base64.urlsafe_b64decode(public_key['n'] + '==')
        e = base64.urlsafe_b64decode(public_key['e'] + '==')
        
        # RSA 공개키 생성
        public_numbers = rsa.RSAPublicNumbers(
            int.from_bytes(e, 'big'),
            int.from_bytes(n, 'big')
        )
        public_key_obj = public_numbers.public_key()
        
        # PEM 형식으로 변환
        pem_public_key = public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # 5. JWT 토큰 디버깅 (audience 확인)
        import base64
        import json
        
        # JWT 토큰을 수동으로 파싱하여 payload 확인
        parts = identity_token.split('.')
        if len(parts) != 3:
            raise Exception("잘못된 JWT 토큰 형식")
        
        # payload 디코딩 (base64url)
        payload_encoded = parts[1]
        # base64url 패딩 추가
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        print(f"🔍 JWT 토큰 audience: {payload.get('aud')}")
        print(f"🔍 설정된 CLIENT_ID: {client_id}")
        
        # 6. 공개키로 JWT 검증 (실제 audience 사용)
        decoded_token = jwt.decode(
            identity_token,
            pem_public_key,
            algorithms=['RS256'],
            audience=payload.get('aud'),  # 실제 audience 사용
            issuer='https://appleid.apple.com'
        )
        
        return decoded_token
        
    except Exception as e:
        print(f"애플 ID 토큰 검증 실패: {e}")
        raise Exception(f"애플 ID 토큰 검증 실패: {e}")

@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_apple_login(request):
    """
    Flutter 앱에서 호출하는 애플 로그인 API
    애플 ID 토큰을 검증하고 JWT 토큰을 반환
    """
    try:
        # Flutter 앱에서 전송한 데이터
        identity_token = request.data.get('identity_token')
        user_identifier = request.data.get('user_identifier')
        email = request.data.get('email')
        full_name = request.data.get('full_name', '애플 사용자')
        fcm_token = request.data.get('fcm_token')  # 🔧 추가: FCM 토큰
        
        if not identity_token:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'identity_token이 필요합니다'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 애플 ID 토큰 검증
        apple_user_info = verify_apple_id_token(
            identity_token, 
            settings.SOCIAL_AUTH_APPLE_CLIENT_ID
        )
        
        # 사용자 정보 추출
        apple_user_id = apple_user_info.get('sub')  # 애플 사용자 고유 ID
        apple_email = apple_user_info.get('email') or email  # 토큰에서 이메일이 없으면 요청에서 가져옴
        
        if not apple_email:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': '이메일 정보를 찾을 수 없습니다'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 기존 사용자 확인
            user = User.objects.get(email=apple_email)
            
            if user.provider == 'apple' or user.login_type == 'hybrid':
                # 이미 애플 로그인으로 가입된 사용자 또는 통합된 사용자
                
                # 🔧 추가: FCM 토큰 업데이트 (다를 때만)
                if fcm_token and user.fcm_token != fcm_token:
                    user.fcm_token = fcm_token
                    user.save(update_fields=['fcm_token'])
                
                response = Response(status=status.HTTP_200_OK)  # 200: 기존 사용자 로그인
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                
                response.data = {
                    'status': status.HTTP_200_OK,
                    'message': '기존 사용자 로그인 성공',
                    'login_type': 'existing',  # 프론트에서 구분용
                    'data': {
                        'access_token': access_token,
                        'refresh_token': str(refresh),
                        'user_exists': True,
                        'user_id': user.user_id,
                        'user_name': user.name,
                        'login_type': user.login_type,
                        'provider': user.provider,
                        'needs_integration': False,
                    }
                }
                
                # 리프레시 토큰을 쿠키에 설정
                response.set_cookie(
                    key="refreshtoken",
                    value=str(refresh),
                    httponly=True,
                    secure=True,
                    samesite="None",
                )
                
                return response
            else:
                # 아직 통합되지 않은 계정이면 통합 옵션 제공
                return Response({
                    'status': status.HTTP_200_OK,
                    'message': 'User already exists',
                    'data': {
                        'user_exists': True,
                        'existing_user_id': user.user_id,
                        'existing_user_name': user.name or 'Unknown',
                        'login_type': user.login_type or 'general',
                        'provider': user.provider or 'none',
                        'needs_integration': True,  # 통합 필요 표시
                    }
                }, content_type='application/json; charset=utf-8')
                
        except User.DoesNotExist:
            # 🔧 수정: 신규 사용자는 임시 ID로 생성하고 추가 정보 입력 페이지로 리다이렉트
            import uuid
            temp_user_id = f"temp_{str(uuid.uuid4())[:8]}_apple"
            
            # 임시 사용자 생성 (추가 정보 입력 완료 후 실제 ID로 업데이트)
            temp_user = User.objects.create(
                user_id=temp_user_id,
                email=apple_email,
                name=full_name,
                provider='apple',
                fcm_token=fcm_token,
                is_active=True
            )
            
            return Response({
                'status': status.HTTP_226_IM_USED,  # 226: 추가 정보 입력 필요
                'message': '추가 정보 입력이 필요합니다',
                'data': {
                    'temp_user_id': temp_user_id,
                    'email': apple_email,
                    'display_name': full_name,
                    'provider': 'apple',
                    'requires_additional_info': True
                }
            }, status=status.HTTP_226_IM_USED)
            
    except Exception as e:
        print(f"애플 로그인 오류: {e}")
        return Response({
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def integrate_apple_account(request):
    """
    기존 계정을 애플 계정과 통합하는 API
    """
    try:
        email = request.data.get('email')
        identity_token = request.data.get('identity_token')
        full_name = request.data.get('full_name')
        
        if not email or not identity_token:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'email and identity_token are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 애플 ID 토큰 검증
        apple_user_info = verify_apple_id_token(
            identity_token, 
            settings.SOCIAL_AUTH_APPLE_CLIENT_ID
        )
        
        try:
            # 기존 사용자 찾기
            user = User.objects.get(email=email)
            
            # 애플 계정 정보로 업데이트 (하이브리드 로그인 지원)
            user.login_type = 'hybrid'  # 일반 로그인 + 소셜 로그인 모두 지원
            user.provider = 'apple'
            if full_name and not user.name:
                user.name = full_name
            user.save()
            
            print(f"✅ 애플 계정 통합 완료: {user.email} -> provider: {user.provider}, login_type: {user.login_type}")
            
            # JWT 토큰 생성하여 반환
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            
            return Response({
                'status': status.HTTP_200_OK,
                'message': 'Account integration successful',
                'data': {
                    'access_token': access_token,
                    'refresh_token': str(refresh),
                    'user_exists': False,  # 통합 완료
                    'integrated_user_id': user.user_id,
                    'integrated_user_name': user.name,
                }
            }, content_type='application/json; charset=utf-8')
            
        except User.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        print(f"애플 계정 통합 오류: {e}")
        return Response({
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': f'Internal server error: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_user_id_availability(request):
    """
    사용자 ID 중복 확인
    """
    try:
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'user_id가 필요합니다'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 중복 확인
        is_available = not User.objects.filter(user_id=user_id).exists()
        
        return Response({
            'status': status.HTTP_200_OK,
            'data': {
                'user_id': user_id,
                'is_available': is_available
            }
        })
        
    except Exception as e:
        return Response({
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': f'사용자 ID 확인 중 오류가 발생했습니다: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def complete_social_registration(request):
    """
    소셜 로그인 사용자의 추가 정보 입력 완료
    """
    try:
        temp_user_id = request.data.get('temp_user_id')
        final_user_id = request.data.get('user_id')
        student_id = request.data.get('student_id')
        name = request.data.get('name')  # 🔧 추가: 닉네임 받기
        
        if not temp_user_id or not final_user_id:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': 'temp_user_id와 user_id가 필요합니다'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 임시 사용자 조회
        try:
            temp_user = User.objects.get(user_id=temp_user_id)
        except User.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': '임시 사용자를 찾을 수 없습니다'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 최종 사용자 ID 중복 확인
        if User.objects.filter(user_id=final_user_id).exists():
            return Response({
                'status': status.HTTP_409_CONFLICT,
                'message': '이미 사용 중인 사용자 ID입니다'
            }, status=status.HTTP_409_CONFLICT)
        
        # 사용자 정보 업데이트
        temp_user.user_id = final_user_id
        temp_user.student_id = student_id
        if name:  # 🔧 추가: 닉네임이 있으면 업데이트
            temp_user.name = name
        temp_user.save()
        
        # JWT 토큰 생성
        refresh = RefreshToken.for_user(temp_user)
        access_token = str(refresh.access_token)
        
        return Response({
            'status': status.HTTP_201_CREATED,
            'message': '회원가입이 완료되었습니다',
            'data': {
                'access_token': access_token,
                'refresh_token': str(refresh),
                'user_id': final_user_id,
                'email': temp_user.email,
                'name': temp_user.name,
                'provider': temp_user.provider
            }
        })
        
    except Exception as e:
        return Response({
            'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'message': f'회원가입 완료 중 오류가 발생했습니다: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)