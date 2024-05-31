# golbang/accounts/views.py

from json import JSONDecodeError
from django.http import JsonResponse
import requests
import os
from rest_framework import status
from .models import *
from allauth.socialaccount.models import SocialAccount
from django.shortcuts import redirect

from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.google import views as google_view

import json
import logging

logger = logging.getLogger(__name__)

# 구글 소셜로그인 변수 설정
state = os.environ.get("STATE")
BASE_URL = 'http://localhost:8000/'
GOOGLE_CALLBACK_URI = BASE_URL + 'accounts/google/callback/'

'''
구글 로그인
'''
# def google_login(request):
#     scope = "https://www.googleapis.com/auth/userinfo.email"
#     client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
#     return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code&redirect_uri={GOOGLE_CALLBACK_URI}&scope={scope}")


def google_login(request):
    scope = "https://www.googleapis.com/auth/userinfo.email"
    client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
    #redirect_uri = os.environ.get("GOOGLE_CALLBACK_URI", "http://localhost:8000/accounts/google/callback/")
    redirect_uri = GOOGLE_CALLBACK_URI  # 환경 변수에서 가져오지 않고 직접 사용
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}")    

'''
access token & 이메일 요청 -> 회원가입/로그인 & jwt 발급
'''
# def google_callback(request):
#     client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
#     client_secret = os.environ.get("SOCIAL_AUTH_GOOGLE_SECRET")
#     code = request.GET.get('code')
    
#     # 1. 받은 코드로 구글에 access token 요청
#     token_req = requests.post(f"https://oauth2.googleapis.com/token?client_id={client_id}&client_secret={client_secret}&code={code}&grant_type=authorization_code&redirect_uri={GOOGLE_CALLBACK_URI}&state={state}")

#     ## 1-1. json으로 변환 & 에러부분 파싱
#     token_req_json = token_req.json()
#     error = token_req_json.get("error")

#     ## 1-2. 에러 발생 시 종료
#     if error is not None:
#         raise JSONDecodeError(error)
    
#     ## 1-3. 성공할 시 access token 가져오기
#     access_token = token_req_json.get('access_token')

#     #################################################################

#     # 2. 가져온 access token으로 이메일값을 구글에 요청
#     email_req = requests.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}")
#     email_req_status = email_req.status_code

#     ## 2-1. 에러 발생 시 400 에러 반환
#     if email_req_status != 200:
#         return JsonResponse({'err_msg': 'failed to get email'}, status=status.HTTP_400_BAD_REQUEST)

#     ## 2-2. 성공 시 이메일 가져오기
#     email_req_json = email_req.json()
#     email = email_req_json.get('email')

#     #################################################################

#     # 3. 전달받은 이메일, access_token, code를 바탕으로 회원가입/로그인
#     try:
#         # 3-1. 전달받은 이메일로 등록된 유저가 있는지 탐색
#         user = User.objects.get(email=email)

#         # 3-2. FK로 연결되어 있는 socialaccount 테이블에서 해당 이메일의 유저가 있는지 확인
#         social_user = SocialAccount.objects.get(user=user)

#         # 3-3. 에러
#         ## 존재하지 않을 경우
#         if social_user is None:
#             return JsonResponse({'err_msg': 'email exists but not social user'}, status=status.HTTP_400_BAD_REQUEST)
#         ## 있는데 구글계정이 아닐 경우에도 에러
#         if social_user.provider != 'google':
#             return JsonResponse({'err_msg': 'no matching social type'}, status=status.HTTP_400_BAD_REQUEST)
        
#         # 3-4. 이미 Google로 제대로 가입된 유저 => 로그인 & 해당 우저의 jwt 발급
#         data = {'access_token': access_token, 'code': code}
#         accept = requests.post(f"{BASE_URL}accounts/google/login/finish/", data=data)
#         accept_status = accept.status_code

#         # 3-5. 에러 발생 시 에러 메시지 출력
#         if accept_status != 200:
#             return JsonResponse({'err_msg': 'failed to signin'}, status=accept_status)
        
#         accept_json = accept.json()
#         accept_json.pop('user', None)
#         return JsonResponse(accept_json)
    
#     except User.DoesNotExist:
#         # 전달받은 이메일로 기존에 가입된 유저가 아예 없으면 
#         # => 새로 회원가입 & 해당 유저의 jwt 발급
#         data = {'access_token': access_token, 'code': code}
#         accept = requests.post(f"{BASE_URL}accounts/google/login/finish/", data=data)
#         accept_status = accept.status_code

#         # 에러가 생긴다면 에러처리
#         if accept_status != 200:
#             return JsonResponse({'err_msg': 'failed to signup', 'status_code': accept_status, 'response': accept.json()}, status=accept_status)
        
#         accept_json = accept.json()
#         accept_json.pop('user', None)
#         return JsonResponse(accept_json)


#     except SocialAccount.DoesNotExist:
#     	# User는 있는데 SocialAccount가 없을 때 (=일반회원으로 가입된 이메일일때)
#         return JsonResponse({'err_msg': 'email exists but not social user'}, status=status.HTTP_400_BAD_REQUEST)
def google_callback(request):
    try:
        client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("SOCIAL_AUTH_GOOGLE_SECRET")
        code = request.GET.get('code')
        
        # 1. 받은 코드로 구글에 access token 요청
        token_req = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': GOOGLE_CALLBACK_URI,
                'state': state,
            }
        )

        # 1-1. json으로 변환 & 에러부분 파싱
        try:
            token_req_json = token_req.json()
        except json.JSONDecodeError:
            logger.error(f"Token request failed: {token_req.text}")
            return JsonResponse({'err_msg': 'failed to get token', 'response': token_req.text}, status=status.HTTP_400_BAD_REQUEST)

        error = token_req_json.get("error")

        # 1-2. 에러 발생 시 종료
        if error is not None:
            return JsonResponse({'err_msg': 'failed to get token', 'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        # 1-3. 성공할 시 access token 가져오기
        access_token = token_req_json.get('access_token')

        #################################################################

        # 2. 가져온 access token으로 이메일값을 구글에 요청
        email_req = requests.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}")
        email_req_status = email_req.status_code

        # 2-1. 에러 발생 시 400 에러 반환
        if email_req_status != 200:
            return JsonResponse({'err_msg': 'failed to get email', 'status_code': email_req_status}, status=status.HTTP_400_BAD_REQUEST)

        # 2-2. 성공 시 이메일 가져오기
        email_req_json = email_req.json()
        email = email_req_json.get('email')

        #################################################################

        # 3. 전달받은 이메일, access_token, code를 바탕으로 회원가입/로그인
        try:
            # 3-1. 전달받은 이메일로 등록된 유저가 있는지 탐색
            user = User.objects.get(email=email)

            # 3-2. FK로 연결되어 있는 socialaccount 테이블에서 해당 이메일의 유저가 있는지 확인
            social_user = SocialAccount.objects.get(user=user)

            # 3-3. 에러
            # 존재하지 않을 경우
            if social_user is None:
                return JsonResponse({'err_msg': 'email exists but not social user'}, status=status.HTTP_400_BAD_REQUEST)
            # 있는데 구글계정이 아닐 경우에도 에러
            if social_user.provider != 'google':
                return JsonResponse({'err_msg': 'no matching social type'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 3-4. 이미 Google로 제대로 가입된 유저 => 로그인 & 해당 우저의 jwt 발급
            data = {'access_token': access_token, 'code': code}
            logger.debug(f"Sending data to /accounts/google/login/finish/: {data}")
            accept = requests.post(f"{BASE_URL}accounts/google/login/finish/", json=data)  # 데이터를 JSON 형식으로 전송
            accept_status = accept.status_code

            # 3-5. 에러 발생 시 에러 메시지 출력
            if accept_status != 200:
                logger.error(f"Signin failed: {accept.text}")
                return JsonResponse({'err_msg': 'failed to signin', 'status_code': accept_status, 'response': accept.text}, status=accept_status)
            
            try:
                accept_json = accept.json()
            except json.JSONDecodeError:
                logger.error(f"JSON decode error: {accept.text}")
                return JsonResponse({'err_msg': 'failed to signin', 'response': accept.text}, status=accept_status)

            accept_json.pop('user', None)
            return JsonResponse(accept_json)
        
        except User.DoesNotExist:
            # 전달받은 이메일로 기존에 가입된 유저가 아예 없으면 
            # => 새로 회원가입 & 해당 유저의 jwt 발급
            data = {'access_token': access_token, 'code': code}
            logger.debug(f"Sending data to /accounts/google/login/finish/ for signup: {data}")
            accept = requests.post(f"{BASE_URL}accounts/google/login/finish/", json=data)  # 데이터를 JSON 형식으로 전송
            accept_status = accept.status_code

            # 에러가 생긴다면 에러처리
            if accept_status != 200:
                logger.error(f"Signup failed: {accept.text}")
                return JsonResponse({'err_msg': 'failed to signup', 'status_code': accept_status, 'response': accept.text}, status=accept_status)
            
            try:
                accept_json = accept.json()
            except json.JSONDecodeError:
                logger.error(f"JSON decode error: {accept.text}")
                return JsonResponse({'err_msg': 'failed to signup', 'response': accept.text}, status=accept_status)

            accept_json.pop('user', None)
            return JsonResponse(accept_json)

        except SocialAccount.DoesNotExist:
            # User는 있는데 SocialAccount가 없을 때 (=일반회원으로 가입된 이메일일때)
            return JsonResponse({'err_msg': 'email exists but not social user'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.exception("Unexpected error occurred during Google callback")
        return JsonResponse({'err_msg': 'unexpected error', 'exception': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


'''
구글 소셜로그인 뷰
'''
# class GoogleLogin(SocialLoginView):
#     adapter_class = google_view.GoogleOAuth2Adapter
#     callback_url = GOOGLE_CALLBACK_URI
#     client_class = OAuth2Client      


class GoogleLogin(SocialLoginView):
    adapter_class = google_view.GoogleOAuth2Adapter

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            response_content = response.content.decode('utf-8')  # 문자열을 JSON으로 변환
            try:
                response_json = json.loads(response_content)
                logger.debug(f"Google login response: {response_json}")
                return JsonResponse(response_json)
            except json.JSONDecodeError:
                logger.error(f"JSON decode error: {response_content}")
                return JsonResponse({'err_msg': 'error during Google login', 'response': response_content}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception("Error during Google login")
            return JsonResponse({'err_msg': 'error during Google login', 'exception': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
