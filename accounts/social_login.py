'''
MVP demo ver 0.0.1
2024.06.27
accounts/social_login.py

역할: 사용자가 소셜 로그인 시, 사용자 정보를 처리하는 view
- 코드 가독성과 유지보수성을 높이기 위해 views.py로부터 파일을 분리
기능:
- 구글, 네이버, 카카오
'''
from django.conf import settings
from django.urls import reverse
import requests
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from json import JSONDecodeError
from auth.authenticate import generate_access_token, jwt_login  # JWT 토큰 생성하고 로그인 처리하는 함수 

User = get_user_model()

# 구글 로그인
@api_view(['GET'])
@permission_classes([AllowAny])
def google_login(request):
    """
    구글 로그인 URL로 리디렉션
    """
    google_client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?response_type=code"
        f"&client_id={google_client_id}&redirect_uri={redirect_uri}"
        f"&scope=openid%20email%20profile"
    )
    return redirect(google_auth_url)

@api_view(['GET'])
@permission_classes([AllowAny])
def google_callback(request):
    """
    구글 OAuth2 콜백 처리
    """
    code = request.GET.get('code')
    if not code:
        return redirect('google_login')

    google_client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
    google_client_secret = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
    access_token = token_json.get('access_token')
    id_token = token_json.get('id_token')

    user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    user_info_response = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
    user_info = user_info_response.json()

    email = user_info.get("email")
    name = user_info.get("name")
    if not name:
        name = "Unknown"
    if not email:
        return redirect('google_login')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        password = User.objects.make_random_password()
        user = User.objects.create(
            email=email,
            userId=f"{email.split('@')[0]}_google",
            name=name,
            login_type='social',
            provider='google',
            password=password
        )
        user.save()

    # JWT 토큰 생성 및 설정
    response = Response(status=status.HTTP_200_OK)
    response = jwt_login(response, user)

    return response

# 네이버 로그인
@api_view(['GET'])
@permission_classes([AllowAny])
def naver_login(request):
    """
    네이버 로그인 URL로 리디렉션
    """
    client_id = settings.SOCIAL_AUTH_NAVER_CLIENT_ID
    response_type = "code"
    redirect_uri = request.build_absolute_uri(reverse('naver_callback'))
    state = settings.STATE
    url = "https://nid.naver.com/oauth2.0/authorize"
    return redirect(
        f'{url}?response_type={response_type}&client_id={client_id}&redirect_uri={redirect_uri}&state={state}'
    )

@api_view(['GET'])
@permission_classes([AllowAny])
def naver_callback(request):
    """
    네이버 OAuth2 콜백 처리
    """
    try:
        grant_type = 'authorization_code'
        client_id = settings.SOCIAL_AUTH_NAVER_CLIENT_ID
        client_secret = settings.SOCIAL_AUTH_NAVER_CLIENT_SECRET
        code = request.GET.get('code')
        state = request.GET.get('state')

        parameters = f"grant_type={grant_type}&client_id={client_id}&client_secret={client_secret}&code={code}&state={state}"

        token_request = requests.get(
            f"https://nid.naver.com/oauth2.0/token?{parameters}"
        )

        token_response_json = token_request.json()
        error = token_response_json.get("error", None)

        if error is not None:
            raise JSONDecodeError(error)

        access_token = token_response_json.get("access_token")

        user_info_request = requests.get(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_info_request.status_code != 200:
            return JsonResponse({"error": "failed to get user info"}, status=status.HTTP_400_BAD_REQUEST)

        user_info = user_info_request.json().get("response")
        print("NAVER USER INFO:", user_info)  # 디버깅을 위한 출력

        naver_id = user_info.get("id")
        name = user_info.get("name")
        email = user_info.get("email")

        if not name:
            name = "Unknown"

        if not naver_id:
            return JsonResponse({
                "error": "Can't Get ID Information from Naver",
                "user_info": user_info
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            password = User.objects.make_random_password()
            user = User.objects.create(
                email=email,
                userId=f"{email.split('@')[0]}_naver",
                name=name,
                login_type='social',
                provider='naver',
                password=password
        )
        user.save()

        # JWT 토큰 생성 및 설정
        response = Response(status=status.HTTP_200_OK)
        response = jwt_login(response, user)

        return response

    except Exception as e:
        return JsonResponse({
            "error": str(e),
        }, status=status.HTTP_404_NOT_FOUND)

# 카카오 로그인
@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_login(request):
    """
    카카오 로그인 URL로 리디렉션
    """
    kakao_rest_api_key = settings.SOCIAL_AUTH_KAKAO_CLIENT_ID
    redirect_uri = request.build_absolute_uri(reverse('kakao_callback'))
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?response_type=code"
        f"&client_id={kakao_rest_api_key}&redirect_uri={redirect_uri}"
    )
    return redirect(kakao_auth_url)

@api_view(['GET'])
@permission_classes([AllowAny])
def kakao_callback(request):
    """
    카카오 OAuth2 콜백 처리
    """
    code = request.GET.get('code')
    if not code:
        return redirect('kakao_login')

    kakao_rest_api_key = settings.SOCIAL_AUTH_KAKAO_CLIENT_ID
    kakao_secret_key = settings.SOCIAL_AUTH_KAKAO_CLIENT_SECRET
    redirect_uri = request.build_absolute_uri(reverse('kakao_callback'))
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": kakao_rest_api_key,
        "client_secret": kakao_secret_key,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
    access_token = token_json.get('access_token')

    user_info_url = "https://kapi.kakao.com/v2/user/me"
    user_info_response = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
    user_info = user_info_response.json()

    print("KAKAO USER INFO:", user_info)  # 디버깅을 위한 출력

    kakao_account = user_info.get("kakao_account")
    email = kakao_account.get("email")
    nickname = kakao_account.get("profile").get("nickname")

    if not nickname:
        nickname = "Unknown"

    if not email:
        return JsonResponse({
            "error": "Can't Get Email Information from Kakao",
            "user_info": user_info
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        password = User.objects.make_random_password()
        user = User.objects.create(
            email=email,
            userId=f"{email.split('@')[0]}_kakao",
            name=nickname,
            login_type='social',
            provider='kakao',
            password=password
        )
        user.save()

    # JWT 토큰 생성 및 설정
    response = Response(status=status.HTTP_200_OK)
    response = jwt_login(response, user)

    return response
