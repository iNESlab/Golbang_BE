'''
MVP demo ver 0.0.6
2024.08.27
accounts/participants_view.py

역할: Django Rest Framework(DRF)를 사용하여 API 엔드포인트의 로직을 처리
현재 기능:
- 일반 회원가입
- 소셜 회원가입 & 로그인, 로그인 성공
- 회원 전체 조회, 회원정보 조회, 수정
- 비밀번호 인증, 변경
'''

from rest_framework import status, viewsets  # HTTP 응답 상태 코드를 제공하는 모듈
from rest_framework.decorators import api_view, permission_classes, action  # 함수기반 API 뷰, 뷰에 대한 접근 권한
from rest_framework.permissions import AllowAny, IsAuthenticated  # 권한 클래스
from rest_framework.response import Response                        # API 응답 생성
from rest_framework.views import APIView

from accounts.serializers import UserSerializer, UserInfoSerializer
from accounts.forms import UserCreationFirstStepForm, UserCreationSecondStepForm
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from django.http import QueryDict


User = get_user_model()

# 회원가입 step 1 
@api_view(['POST']) # 유저 데이터 생성
@permission_classes([AllowAny]) # 누구나 접근 가능
def signup_first_step(request):
    """
    회원가입 첫 단계 - 사용자 기본 정보 입력
    """
    form = UserCreationFirstStepForm(data=request.data)
    if form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password1"])
        user.save()
        return Response({
            "status": status.HTTP_201_CREATED,
            "message": "First step completed successfully",
            "data": {
                "user_id": user.id
            }
        }, status=status.HTTP_201_CREATED)
    else:
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
# def signup(request):
#     serializer = UserSerializer(data=request.data) # 요청 데이터를 이용해 UserSerializer 객체 생성
    
#     if serializer.is_valid(raise_exception=True):   # 직렬화된 데이터 유효성 검증 (유효하지 않은 경우, 예외 발생 -> 404 Bad Request 응답 반환)
#         user = serializer.save()                    # 유효한 데이터를 저장하여 새로운 사용자 객체를 생성
#         user.set_password(request.data.get('password')) # password는 해시화하여 저장
#         user.save() # 객체를 DB에 저장
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
    
# 회원가입 step 2
@api_view(['POST'])
@permission_classes([AllowAny])
def signup_second_step(request):
    """
    회원가입 두 번째 단계 - 추가 정보 입력
    """
    user_id = request.data.get('user_id')
    if not user_id:
        return Response({
            "status": status.HTTP_400_BAD_REQUEST,
            "message": "user_id is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            "status": status.HTTP_404_NOT_FOUND,
            "message": "User not found"
        }, status=status.HTTP_404_NOT_FOUND)
    
    form = UserCreationSecondStepForm(data=request.data, instance=user)
    if form.is_valid():
        form.save()
        return Response({
            "status": status.HTTP_200_OK,
            "message": "Second step completed successfully"
        }, status=status.HTTP_200_OK)
    else:
        return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

# 소셜 회원가입 & 로그인
def social_login(request):
    """
    소셜 로그인 테스트 페이지 렌더링
    """
    return render(request, 'login.html')

def login_success(request):
    """
    로그인 성공 페이지 렌더링
    """
    user_email = request.session.get('user_email')
    if not user_email:
        return redirect('social_login')

    user = User.objects.get(email=user_email)
    print("로그인 성공: ", user)
    return render(request, 'login_success.html', {'user': user})

'''
회원정보
'''
class UserInfoViewSet(viewsets.ModelViewSet):
    """
    사용자 정보 조회 및 수정 ViewSet
    """
    queryset = User.objects.all()  # 모든 사용자 조회
    serializer_class = UserInfoSerializer
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    def list(self, request, *args, **kwargs):
        """
        전체 사용자 목록을 조회
        """
        users = self.get_queryset()  # 모든 사용자 쿼리셋 가져오기
        serializer = self.get_serializer(users, many=True)
        return Response({
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved user list',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """
        특정 사용자 정보 조회
        """
        instance = self.get_object()  # 특정 사용자 객체 가져오기
        serializer = self.get_serializer(instance)
        return Response({
            "status": status.HTTP_200_OK,
            "message": "Successfully retrieved user info",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        """
        특정 사용자 정보 수정
        """
        instance = self.get_object()

        # 프로필 이미지 삭제 로직 추가: 클라이언트가 빈 문자열을 전송한 경우 None(null)로 처리
        if 'profile_image' in request.data:
            profile_image = request.data.get('profile_image')
            if profile_image == '':  # 빈 문자열인 경우
                # request.data가 QueryDict인지 확인
                if isinstance(request.data, QueryDict):
                    request.data._mutable = True  # 수정 가능 상태로 설정
                    request.data['profile_image'] = None  # 빈 문자열을 None으로 변환
                    request.data._mutable = False  # 다시 수정 불가 상태로 전환
                else:
                    # 일반 딕셔너리인 경우 바로 수정 가능
                    request.data['profile_image'] = None

        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'messages': 'Invalid data',
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        read_serializer = self.get_serializer(user)
        return Response({
            'status': status.HTTP_200_OK,
            'message': 'Successfully updated user info',
            'data': read_serializer.data
        }, status=status.HTTP_200_OK)


class PasswordManagementView(APIView):
    '''
    비밀번호 변경
    '''
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        action = kwargs.get('action')

        if action == 'verify':
            return self.verify_password(request)
        elif action == 'change':
            return self.change_password(request)
        else:
            return Response({
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid action"
            }, status=status.HTTP_400_BAD_REQUEST)

    def verify_password(self, request):
        current_password = request.data.get('current_password')
        user = request.user

        if not user.check_password(current_password):
            return Response({
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "Current password is incorrect"
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": status.HTTP_200_OK,
            "message": "Password verified successfully"
        }, status=status.HTTP_200_OK)

    def change_password(self, request):
        new_password = request.data.get('new_password')
        user = request.user

        if not new_password:
            return Response({
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "New password is required"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({
            "status": status.HTTP_200_OK,
            "message": "Password updated successfully"
        }, status=status.HTTP_200_OK)