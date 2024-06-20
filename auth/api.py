'''
MVP demo ver 0.0.1
2024.06.20
auth/api.py

역할: DRF REST API
목적: views.py 파일 내의 복잡성을 줄이고, 인증 관련 로직을 별도의 파일로 분리하기 위해 만든 파일
기능: JWT 인증을 사용한 로그인, 로그아웃, 토큰 갱신
'''

import jwt
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response    # API의 응답
from django.contrib.auth import get_user_model, authenticate  # 현재 활성화된 사용자 모델, 인증
from django.conf import settings                # Django 프로젝트의 설정 파일
from django.utils.decorators import method_decorator    # 클래스 기반 뷰애 데코레이터 적용하기 위한 함수형 데코레이터
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie  # CSRF 보호를 위한 데코레이터
from auth.authenticate import generate_access_token, jwt_login # JWT 토큰 생성하고 로그인 처리하는 함수 
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken # RefreshToken

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
        key값 : email, password
        '''
        # 요청 데이터로부터 이메일 또는 아이디가 들어간 username필드와 비밀번호 가져옴
        username_or_email = request.data.get('username')
        password = request.data.get('password')
        
        # 이메일이나 비밀번호가 없을 경우 -> 400 bad request 응답
        if (username_or_email is None) or (password is None):
            return Response({
                "message": "username/email and password required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 인증
        user = authenticate(username=username_or_email, password=password)

        ## 사용자가 없는 경우 -> 404 not found 응답
        if user is None:
            return Response({
                "message": "유저를 찾을 수 없습니다"
            }, status=status.HTTP_404_NOT_FOUND)
        ## 비밀번호가 일치하지 않는 경우 -> 400 bad request응답
        if not user.check_password(password):
            return Response({
                "message": "비밀번호가 일치하지 않습니다"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        response = Response(status=status.HTTP_200_OK)  # 200 OK 응답 객체 생성하여
        return jwt_login(response, user)                # jwt_login 함수 호출하면서 응답객체에 토큰 설정하고 반환
        

'''
JWT 토큰 갱신 로직을 처리하는 클래스 기반 뷰
'''
@method_decorator(csrf_protect, name='dispatch') # 뷰가 호출될 때마다 CSRF 보호를 적용
class RefreshJWTToken(APIView):
    def post(self, request, *args, **kwargs): # HTTP POST 요청을 처리
        refresh_token = request.COOKIES.get('refreshtoken') # 요청 쿠키에서 리프레시 토큰을 가져옴
        
        # 리프레시 토큰이 제공되지 않는 경우 -> 403 Forbidden 응답
        if refresh_token is None:
            return Response({
                "message": "Authentication credentials were not provided."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # JWT 디코딩 
        try:
            payload = jwt.decode(
                # 프레시 토큰을 디코딩하여 페이로드를 가져옴
                refresh_token, settings.REFRESH_TOKEN_SECRET, algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError: # 리프레시 토큰이 만료된 경우 예외처리 -> 403 Forbidden
            return Response({
                "message": "expired refresh token, please login again."
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 페이로드에서 가져온 사용자 ID로 사용자를 조회
        user = User.objects.filter(id=payload['user_id']).first()
        
        # 예외처리
        ## 사용자가 없는 경우 -> 400 Bad Request 응답
        if user is None:
            return Response({
                "message": "user not found"
            }, status=status.HTTP_400_BAD_REQUEST)
        ## 사용자가 비활성화된 경우 -> 400 Bad Request 응답
        if not user.is_active:
            return Response({
                "message": "user is inactive"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 새 엑세스 토큰 생성
        access_token = generate_access_token(user)
        
        return Response( # 새 액세스 토큰을 포함하여 200 OK 응답을 반환
            {
                'access_token': access_token,
            }
        )
        
'''
로그아웃 로직을 처리하는 클래스 기반 뷰
'''        
@method_decorator(csrf_protect, name='dispatch') # 뷰가 호출될 때마다 CSRF 보호를 적용
class LogoutApi(APIView):
    permission_classes = [AllowAny]  # 로그인 엔드포인트에 대한 접근 권한 설정

    def post(self, request): # HTTP POST 요청을 처리
        '''
        클라이언트 refreshtoken 쿠키를 삭제하여 로그아웃처리
        '''
        try:
            # 202 Accepted 응답 객체를 생성
            response = Response({
                "message": "Logout success"
                }, status=status.HTTP_202_ACCEPTED)
            response.delete_cookie('refreshtoken') # 응답 객체에서 리프레시 토큰 쿠키를 삭제

            return response
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


