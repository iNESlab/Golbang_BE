'''
MVP demo ver 0.0.6
2024.08.27
accounts/participants_view.py

역할: Django Rest Framework(DRF)를 사용하여 API 엔드포인트의 로직을 처리
현재 기능:
- 일반 회원가입
- 소셜 회원가입 & 로그인, 로그인 성공
- 회원 전체 조회, 회원정보 조회, 수정, 탈퇴
- 비밀번호 인증, 변경
'''
import boto3

from rest_framework import status, viewsets  # HTTP 응답 상태 코드를 제공하는 모듈
from rest_framework.decorators import api_view, permission_classes, action  # 함수기반 API 뷰, 뷰에 대한 접근 권한
from rest_framework.permissions import AllowAny, IsAuthenticated  # 권한 클래스
from rest_framework.response import Response                        # API 응답 생성
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError


from accounts.serializers import UserSerializer, UserInfoSerializer, OtherUserInfoSerializer
from accounts.forms import UserCreationFirstStepForm, UserCreationSecondStepForm
from clubs.views.club_member import ClubMemberViewSet
from clubs.models import ClubMember

from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render
from django.http import QueryDict

from utils.compress_image import compress_image
from utils.delete_s3_image import delete_s3_file

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
                "user_id": user.id # TODO: user_id -> account_id
            }
        }, status=status.HTTP_201_CREATED)
    else:
        return Response({
            "status": status.HTTP_400_BAD_REQUEST,
            "message": "There were errors in the form submission",
            "errors": form.errors  # 여기에 form errors 포함
        }, status=status.HTTP_400_BAD_REQUEST)
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
# TODO: 아래 페이지 삭제
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
    serializer_class = UserInfoSerializer  # 기본 시리얼라이저는 UserInfoSerializer로 설정
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    def get_serializer_class(self):
        """
        사용자 목록을 조회할 때는 OtherUserInfoSerializer 사용,
        특정 사용자 조회나 수정 등에는 UserInfoSerializer 사용
        """
        if self.action == 'list':
            return OtherUserInfoSerializer  # 전체 사용자 목록 조회 시 사용
        return UserInfoSerializer  # 나머지 경우에 사용

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
        print(f"request.data: {request.data}")

        # 프로필 이미지 삭제 요청 처리
        if 'profile_image' in request.data and request.data['profile_image'] == '':
            # 기존 S3에 저장된 프로필 이미지가 있는 경우 삭제 처리
            if instance.profile_image:
                print(f"image_key: {instance.profile_image}")

                # S3 이미지 삭제 함수 호출
                if delete_s3_file("accounts", instance.profile_image):
                    instance.profile_image = None  # 프로필 이미지를 None으로 설정
                    instance.save()

            # 요청 데이터를 수정하여 이미지 필드를 None으로 처리
            if isinstance(request.data, QueryDict):
                request.data._mutable = True
                request.data['profile_image'] = None
                request.data._mutable = False
            else:
                request.data['profile_image'] = None

        try:
            serializer = self.get_serializer(instance, data=request.data, partial=True)

            if not serializer.is_valid():
                print(f"Validation errors: {serializer.errors}")
                return Response({
                    'status': status.HTTP_400_BAD_REQUEST,
                    'messages': 'Invalid data',
                    'error': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()
        except Exception as e:
            print(f"Error while updating user info: {e}")
            return Response({
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'messages': 'An error occurred while updating user info',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            read_serializer = self.get_serializer(user)
            return Response({
                'status': status.HTTP_200_OK,
                'message': 'Successfully updated user info',
                'data': read_serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error while reading updated user info: {e}")
            return Response({
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'messages': 'An error occurred while retrieving updated user info',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def destroy(self, request, *args, **kwargs):
        """
        회원탈퇴 API - 클럽 관리 여부 확인 후 탈퇴 처리
        """
        user = request.user  # 현재 사용자 가져오기
        club_memberships = ClubMember.objects.filter(user=user)  # 사용자가 가입한 클럽 목록 가져오기

        # ClubMemberViewSet 인스턴스 생성
        club_member_viewset = ClubMemberViewSet()

        for membership in club_memberships:
            # 클럽 관리자 여부 확인
            if membership.role == 'admin':
                # 같은 클럽의 다른 관리자가 있는지 확인
                other_admins = ClubMember.objects.filter(
                    club=membership.club,
                    role='admin'
                ).exclude(user=user)

                if not other_admins.exists():
                    # 다른 관리자가 없으면 에러 반환
                    raise ValidationError({
                        "status": status.HTTP_400_BAD_REQUEST,
                        "message": f"Cannot leave the club '{membership.club.name}' because you are the only admin. Please transfer admin rights to another member before deleting your account."
                    })

            # 관리자가 아닌 경우 또는 다른 관리자가 있는 경우, 클럽 나가기 호출
            club_member_viewset.common_leave_club(member=membership, user=user)

        # 유저 데이터 익명화 및 비활성화
        user.name = 'Deleted_User'
        user.phone_number = '000-000-0000'
        user.address = None
        user.date_of_birth = None
        user.student_id = None
        user.profile_image = None
        user.fcm_token = None
        user.provider = None
        user.email = f"deleted_{user.id}@example.com"
        user.is_active = False
        user.save()

        return Response({
            "status": status.HTTP_200_OK,
            "message": "User account successfully anonymized and deactivated"
        }, status=status.HTTP_200_OK)

from django.core.mail import send_mail
from django.utils.crypto import get_random_string

class PasswordManagementView(APIView):
    '''
    비밀번호 변경
    '''

    def get_permissions(self):
        """
        작업(action)에 따라 권한 설정
        """
        action = self.request.resolver_match.kwargs.get('action')

        if action == 'forget':
            return [AllowAny()]  # 비밀번호 잊음은 인증 필요 없음
        return [IsAuthenticated()]  # 나머지는 인증 필요

    def post(self, request, *args, **kwargs):
        action = kwargs.get('action')

        if action == 'verify':
            return self.verify_password(request)
        elif action == 'change':
            return self.change_password(request)
        elif action == 'forget':
            return self.forget_password(request)
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
    
    def forget_password(self, request):
            # 인증 필요 없음
            email = request.data.get('email')

            if not email:
                return Response({
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Email is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(email=email)
                
            except User.DoesNotExist:
                return Response({
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "User with this email does not exist"
                }, status=status.HTTP_404_NOT_FOUND)

            temporary_password = get_random_string(length=8)
            user.set_password(temporary_password)
            user.save()

            subject = "비밀번호 변경 요청: Password Reset Request" # TODO: 제목 앞에 '골방' 넣기
            message = f"안녕하세요 {user.name}님,\n\n임시 비밀번호: {temporary_password}\n\n로그인 후 비밀번호를 변경해주세요."
            message += f"\n\nHello {user.name},\n\nYour temporary password is: {temporary_password}\n\nPlease log in and reset your password immediately."
            from_email = 'your_email@example.com'
            recipient_list = [email]

            send_mail(subject, message, from_email, recipient_list)

            return Response({
                "status": status.HTTP_200_OK,
                "message": "A temporary password has been sent to your email"
            }, status=status.HTTP_200_OK)
