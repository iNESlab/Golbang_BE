'''
MVP demo ver 0.0.1
2024.06.19
accounts/views.py

역할: Django Rest Framework(DRF)를 사용하여 API 엔드포인트의 로직을 처리
현재 기능:
- 회원가입, 로그인
'''

from rest_framework import status                                   # HTTP 응답 상태 코드를 제공하는 모듈
from rest_framework.decorators import api_view, permission_classes  # 함수기반 API 뷰, 뷰에 대한 접근 권한
from rest_framework.permissions import AllowAny                     # 권한 클래스 (누구나 접근 가능; 주로 회원가입이나 로그인과 같은 공개 API에 사용)
from rest_framework.response import Response                        # API 응답 생성 
from rest_framework_simplejwt.tokens import RefreshToken            # JWT 토큰 생성
from django.contrib.auth import authenticate                        # 자격 증명으로 사용자 인증
from django.contrib.auth.models import update_last_login            # 마지막으로 로그인한 시간 업데이트
from accounts.serializers import UserSerializer                     # 사용자 모델의 직렬화 및 역직렬화 처리

# 회원가입
@api_view(['POST']) # 유저 데이터 생성
@permission_classes([AllowAny]) # 누구나 접근 가능
def signup(request):
    serializer = UserSerializer(data=request.data) # 요청 데이터를 이용해 UserSerializer 객체 생성
    
    if serializer.is_valid(raise_exception=True):   # 직렬화된 데이터 유효성 검증 (유효하지 않은 경우, 예외 발생 -> 404 Bad Request 응답 반환)
        user = serializer.save()                    # 유효한 데이터를 저장하여 새로운 사용자 객체를 생성
        user.set_password(request.data.get('password')) # password는 해시화하여 저장
        user.save() # 객체를 DB에 저장
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
# 로그인
@api_view(['POST']) # 로그인 자격 증명 확인
@permission_classes([AllowAny]) # 누구나 접근 가능
def login(request):
    # 이메일과 비밀번호를 가져옴
    email = request.data.get('email')
    password = request.data.get('password')

    user = authenticate(email=email, password=password) # 이메일과 비밀번호를 사용하여 사용자 인증. (유효하지 않을 경우, 'None'이 반환됨)
    
    # 인증에 실패한 경우, 401 Unauthorized 응답을 반환
    if user is None:
        return Response({'message': '아이디 또는 비밀번호가 일치하지 않습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

    # 인증에 성공할 경우, 
    refresh = RefreshToken.for_user(user)   # 새 JWT 리프레시 토큰 생성
    update_last_login(None, user)           # 마지막 로그인 시간 업데이트

    # 새로 생성된 리프레시 토큰과 액세스 토큰을 포함하여 200 OK 반환
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }, status=status.HTTP_200_OK)