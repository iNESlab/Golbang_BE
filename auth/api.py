"""
MVP demo ver 0.0.5
2024.10.21
auth/api.py

역할: DRF REST API
목적: participants_view.py 파일 내의 복잡성을 줄이고, 인증 관련 로직을 별도의 파일로 분리하기 위해 만든 파일
기능: JWT 인증을 사용한 로그인, 로그아웃, 토큰 갱신, 액세스 토큰 만료시 리프레시 토큰과 함께 반환하도록 설정
"""
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response    # API의 응답
from django.contrib.auth import get_user_model, authenticate  # 현재 활성화된 사용자 모델, 인증
from django.utils.decorators import method_decorator    # 클래스 기반 뷰애 데코레이터 적용하기 위한 함수형 데코레이터
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt  # CSRF 보호를 위한 데코레이터

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken # RefreshToken

import logging

User = get_user_model() # 사용자 모델을 변수에 할당

'''
로그인 로직 처리하는 클래스 기반 뷰
'''
@method_decorator(ensure_csrf_cookie, name="dispatch") # 뷰가 호출될 때마다 CSRF 쿠키를 설정
class LoginApi(APIView):
    permission_classes = [AllowAny]  # 로그인 엔드포인트에 대한 접근 권한 설정

    def post(self, request, *args, **kwargs): # HTTP POST 요청
        '''
        이메일과 비밀번호를 통해 로그인 시도
        key값 : username, password
        '''
        # 요청 데이터로부터 이메일 또는 아이디가 들어간 username필드와 비밀번호 가져옴
        userid_or_email = request.data.get('username')
        password        = request.data.get('password')
        fcm_token       = request.data.get('fcm_token')

        # 1. 이메일이나 비밀번호가 없을 경우 -> 400 bad request 응답
        if not userid_or_email and not password:
            logging.error(f"[LOGIN ERROR]Username or email and password are required")
            return Response({
                "status" : status.HTTP_400_BAD_REQUEST,
                "message": "username/email 과 password가 필요합니다"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        elif not userid_or_email:
            logging.error(f"[LOGIN ERROR]Username or email is required")
            return Response({
                "status" : status.HTTP_400_BAD_REQUEST,
                "message": "username/email이 필요합니다"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        elif not password:
            logging.error(f"[LOGIN ERROR]Password is required")
            return Response({
                "status" : status.HTTP_400_BAD_REQUEST,
                "message": "password가 필요합니다"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # 2. 이메일 (또는 username)으로 사용자 검색 
        # 사용자가 없는 경우 -> 404 not found 응답
        try:
            user = User.objects.get(
                Q(user_id__exact=userid_or_email) |
                Q(email__exact=userid_or_email)
            )
        except User.DoesNotExist:
            logging.error(f"[LOGIN ERROR]User does not exist: {userid_or_email}")
            return Response({
                "status": status.HTTP_404_NOT_FOUND,
                "message": "Email 또는 Username을 찾을 수 없습니다."
            }, status=status.HTTP_404_NOT_FOUND)

        # 3. 비밀번호 검증 (비밀번호가 일치하지 않는 경우 -> 400 bad request)
        if not user.check_password(password):
            logging.error(f"[LOGIN ERROR]Password does not match: {userid_or_email}")
            return Response({
                "status" : status.HTTP_400_BAD_REQUEST,
                "message": "비밀번호가 일치하지 않습니다."
            }, status=status.HTTP_400_BAD_REQUEST)

        # FCM 토큰이 비어 있거나 다르면 업데이트
        if fcm_token:
            if user.fcm_token != fcm_token:
                user.fcm_token = fcm_token
                user.save()

        refresh      = RefreshToken.for_user(user)  # SIMPLE_JWT를 활용하여 리프레시 토큰 생성
        access_token = str(refresh.access_token)    # 액세스 토큰 생성

        response_data = {'access_token': access_token}

        response = Response({
            "status": status.HTTP_200_OK,
            "message": "Successfully Logged In",
            "data": response_data,
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            key="refreshtoken",
            value=str(refresh),
            httponly=True,
            secure=True,  # HTTPS에서만 전송
            samesite="None", # 프론트엔드와 백엔드가 서로 다른 도메인일 때
        )
        # 액세스 토큰 만료시 리프레시 토큰과 함께 리턴
        # if is_token_expired(access_token):
        #     response_data['refresh_token'] = str(refresh)
        #     response = Response(response_data, status=status.HTTP_200_OK)
        #     response.set_cookie(key="refreshtoken", value=str(refresh), httponly=True)
        #     return response
        # 액세스 토큰이 만료되지 않았다면 액세스 토큰만 리턴
        return response

'''
JWT 토큰 갱신 로직을 처리하는 클래스 기반 뷰
'''
# TODO: 완성 시 성문이에게 공유
@method_decorator(csrf_exempt, name='dispatch')
class RefreshJWTToken(APIView):
    def post(self, request, *args, **kwargs): # HTTP POST 요청을 처리
        '''
        1. 리프레시 토큰이 쿠키에 저장되어 있으므로, 프론트엔드에서 헤더에 포함하지 않아도 됨
        2. 리프레시 토큰이 유효하면 새 액세스 토큰을 발급하고 반환
        3. 만료된 리프레시 토큰이라면 403 Forbidden 반환 → 사용자는 다시 로그인해야 함
        '''
        refresh_token = request.COOKIES.get('refreshtoken') # 요청 쿠키에서 리프레시 토큰을 가져옴

        # 리프레시 토큰이 제공되지 않는 경우 -> 403 Forbidden 응답
        if refresh_token is None:
            return Response({
                "status" : status.HTTP_403_FORBIDDEN,
                "message": "Authentication credentials were not provided."
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            refresh = RefreshToken(refresh_token)  # SIMPLE_JWT를 활용하여 토큰 검증 및 갱신
            access_token = str(refresh.access_token)  # 새로운 액세스 토큰 발급

            return Response({"access_token": access_token}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": "Invalid or expired refresh token",
                "status": status.HTTP_403_FORBIDDEN,
            }, status=status.HTTP_403_FORBIDDEN)

        # # JWT 디코딩
        # try:
        #     payload = jwt.decode(
        #         # 프레시 토큰을 디코딩하여 페이로드를 가져옴
        #         refresh_token, settings.REFRESH_TOKEN_SECRET, algorithms=['HS256']
        #     )
        # except jwt.ExpiredSignatureError: # 리프레시 토큰이 만료된 경우 예외처리 -> 403 Forbidden
        #     return Response({
        #         "status" : status.HTTP_403_FORBIDDEN,
        #         "message": "Expired refresh token, please login again."
        #     }, status=status.HTTP_403_FORBIDDEN)
        #
        # # 페이로드에서 가져온 사용자 ID로 사용자를 조회
        # user = User.objects.filter(id=payload['user_id']).first()
        #
        # # 예외처리
        # ## 사용자가 없는 경우 -> 404 Not Found 응답
        # if user is None:
        #     return Response({
        #         "status" : status.HTTP_404_NOT_FOUND,
        #         "message": "User not found"
        #     }, status=status.HTTP_404_NOT_FOUND)
        # ## 사용자가 비활성화된 경우 -> 400 Bad Request 응답
        # if not user.is_active:
        #     return Response({
        #         "status" : status.HTTP_400_BAD_REQUEST,
        #         "message": "User is inactive"
        #     }, status=status.HTTP_400_BAD_REQUEST)
        #
        # # 새 엑세스 토큰 생성
        # access_token = generate_access_token(user)
        #
        # return Response( # 새 액세스 토큰을 포함하여 200 OK 응답을 반환
        #     {
        #         'access_token': access_token,
        #     }
        # )

'''
로그아웃 로직을 처리하는 클래스 기반 뷰
'''
# TODO: 사용성 점검. 소셜 로그인 할 때 다시 보기
@method_decorator(csrf_exempt, name='dispatch')
class LogoutApi(APIView):
    permission_classes = [IsAuthenticated]  # 로그인 엔드포인트에 대한 접근 권한 설정

    def post(self, request): # HTTP POST 요청을 처리
        '''
        클라이언트 refreshtoken 쿠키를 삭제하여 로그아웃처리
        '''
        try:
            # 202 Accepted 응답 객체를 생성
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist() # 블랙리스트에 추가하여 무효화

            response = Response({
                "status": status.HTTP_202_ACCEPTED,
                "message": "Successfully Logged Out"
            }, status=status.HTTP_202_ACCEPTED)
            response.delete_cookie('refreshtoken') # 쿠키 삭제

            return response
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)