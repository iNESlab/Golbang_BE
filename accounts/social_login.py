'''
MVP demo ver 0.0.3
2024.06.28
accounts/social_login.py

역할: 사용자가 소셜 로그인 시, 사용자 정보를 처리하는 view
- 코드 가독성과 유지보수성을 높이기 위해 views.py로부터 파일을 분리

기능:
1. 구글, 네이버, 카카오 소셜 로그인
2. 공통된 기능은 헬퍼 함수 처리
- create_user_and_login: 새로운 사용자를 생성하고 JWT 토큰을 반환.
- get_access_token: 주어진 토큰 URL과 데이터로 액세스 토큰을 가져옴.
3. 소셜 로그인 함수 구조 통일하여 가독성, 유지보수성, 일관성 향상
- 각 소셜 로그인 함수(구글, 네이버, 카카오)에서 공통적인 패턴을 따름.
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
from auth.authenticate import generate_access_token, jwt_login  # JWT 토큰 생성하고 로그인 처리하는 함수

User = get_user_model()

def create_user_and_login(response, email, user_id, name, provider):
    """
    새로운 사용자를 생성하고 JWT 토큰을 반환하는 헬퍼 함수
    """
    password = User.objects.make_random_password()  # 소셜 로그인이기 때문에 비밀번호는 랜덤하게 생성
    user = User.objects.create(
        email=email,
        userId=user_id,
        name=name,
        login_type='social',
        provider=provider,
        password=password
    )
    user.save() # user 저장
    response = jwt_login(response, user) # JWT 토큰 생성하고 응답 추가

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
            response = Response(status=status.HTTP_200_OK)
            # response, email, user_id, name, provider
            return create_user_and_login(response, email, f"{email.split('@')[0]}_google", name, 'google')

        response = Response(status=status.HTTP_200_OK)
        response = jwt_login(response, user) # 기존 사용자라면 JWT 토큰 생성

        # JWT 토큰을 JSON 응답으로 반환
        # return JsonResponse({
        #     "access_token": response.data['access_token'],
        #     "refresh_token": response.data['refresh_token'],
        # })
        return response
    
    except Exception as e:
        return JsonResponse({
            "error": str(e),
        }, status=status.HTTP_404_NOT_FOUND)
    
###############
# 네이버 로그인
###############
@api_view(['GET'])
@permission_classes([AllowAny])
def naver_login(request):
    """
    네이버 로그인 URL로 리디렉션
    """
    naver_client_id = settings.SOCIAL_AUTH_NAVER_CLIENT_ID
    redirect_uri    = settings.NAVER_CALLBACK_URL
    state           = settings.STATE
    naver_auth_url = (
        f"https://nid.naver.com/oauth2.0/authorize?response_type=code"
        f"&client_id={naver_client_id}&redirect_uri={redirect_uri}&state={state}"
    )
    return redirect(naver_auth_url)   # 네이버 로그인 페이지로 리디렉션
    #return JsonResponse({"auth_url": naver_auth_url})

@api_view(['GET'])
@permission_classes([AllowAny])
def naver_callback(request):
    """
    네이버 OAuth2 콜백 처리
    """
    try:
        code  = request.GET.get('code') # 네이버에서 반환된 코드 가져옴
        state = request.GET.get('state')

        if not code: # 코드가 없으면 로그인 페이지로 리디렉션
            return redirect('naver_login')
        
        # 인증 코드를 사용하여 소셜 로그인 제공자에게 액세스 토큰을 요청
        token_url = "https://nid.naver.com/oauth2.0/token"
        token_data = {
            "grant_type": "authorization_code",
            "client_id": settings.SOCIAL_AUTH_NAVER_CLIENT_ID,
            "client_secret": settings.SOCIAL_AUTH_NAVER_SECRET,
            "code": code,
            "state": state,
        }
        access_token = get_access_token(token_url, token_data)  # 액세스 토큰 가져옴

        # user_info_url: 소셜 로그인에서 액세스 토큰을 사용하여 사용자 정보를 가져오는 역할
        # 액세스 토큰을 사용하여 사용자 정보를 가져온다.
        user_info_url       = "https://openapi.naver.com/v1/nid/me"
        user_info_response  = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})

        if user_info_response.status_code != 200:
            return JsonResponse({"error": "failed to get user info"}, status=status.HTTP_400_BAD_REQUEST)

        user_info = user_info_response.json().get("response")

        # CHECK SUCCESSFULLY LOGIN PROCESS
        print("===NAVER USER INFO===", user_info)

        email = user_info.get("email")
        name  = user_info.get("name", "Unknown") # 이름이 없으면 "Unknown"으로 설정

        # 이메일이 없으면 로그인 페이지로 리디렉션
        if not email:
            return redirect('naver_login')

        try: # 기존 사용자인지 확인
            user = User.objects.get(email=email)
        except User.DoesNotExist:  # 사용자 정보가 없는 경우 회원가입 진행
            response = Response(status=status.HTTP_200_OK)
            # response, email, user_id, name, provider
            return create_user_and_login(response, email, f"{email.split('@')[0]}_naver", name, 'naver')

        response = Response(status=status.HTTP_200_OK)
        response = jwt_login(response, user)

        return response

    except Exception as e:
        return JsonResponse({
            "error": str(e),
        }, status=status.HTTP_404_NOT_FOUND)

###############
# 카카오 로그인
###############
@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_login(request):
    """
    카카오 로그인 URL로 리디렉션
    """
    kakao_rest_api_key  = settings.SOCIAL_AUTH_KAKAO_CLIENT_ID
    redirect_uri        = settings.KAKAO_CALLBACK_URL
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?response_type=code"
        f"&client_id={kakao_rest_api_key}&redirect_uri={redirect_uri}"
    )
    return redirect(kakao_auth_url) # 카카오 로그인 페이지로 리디렉션
    #return JsonResponse({"auth_url": kakao_auth_url})

@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_callback(request):
    """
    카카오 OAuth2 콜백 처리
    """
    try:
        code = request.GET.get('code') # 카카오에서 반환된 인증 코드 추출
        if not code: # 코드가 없으면 로그인 페이지로 리디렉션
            return redirect('kakao_login')
        
        # 인증 코드를 사용하여 소셜 로그인 제공자에게 액세스 토큰을 요청
        token_url   = "https://kauth.kakao.com/oauth/token"
        token_data  = {
            "grant_type": "authorization_code",
            "client_id": settings.SOCIAL_AUTH_KAKAO_CLIENT_ID,
            "client_secret": settings.SOCIAL_AUTH_KAKAO_SECRET,
            "redirect_uri": request.build_absolute_uri(reverse('kakao_callback')),
            "code": code,
        }
        access_token = get_access_token(token_url, token_data) # 액세스 토큰 가져옴

        # user_info_url: 소셜 로그인에서 액세스 토큰을 사용하여 사용자 정보를 가져오는 역할
        # 액세스 토큰을 사용하여 사용자 정보를 가져온다.
        user_info_url       = "https://kapi.kakao.com/v2/user/me"
        user_info_response  = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
        user_info           = user_info_response.json()

        # CHECK SUCCESSFULLY LOGIN PROCESS
        print("===KAKAO USER INFO===", user_info)

        kakao_account   = user_info.get("kakao_account")
        email           = kakao_account.get("email")
        nickname        = kakao_account.get("profile").get("nickname", "Unknown") # 닉네임이 없으면 "Unknown"으로 설정

        # 이메일이 없으면 로그인 페이지로 리디렉션
        if not email:
            return redirect('kakao_login')

        try: # 기존 사용자인지 확인
            user = User.objects.get(email=email)
        except User.DoesNotExist: # 사용자 정보가 없는 경우 회원가입 진행
            response = Response(status=status.HTTP_200_OK)
            # response, email, user_id, name, provider
            return create_user_and_login(response, email, f"{email.split('@')[0]}_kakao", nickname, 'kakao')

        response = Response(status=status.HTTP_200_OK)
        response = jwt_login(response, user)  # 기존 사용자라면 JWT 토큰 생성

        return response
    
    except Exception as e:
        return JsonResponse({
            "error": str(e),
        }, status=status.HTTP_404_NOT_FOUND)