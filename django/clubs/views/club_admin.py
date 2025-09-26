'''
MVP demo ver 0.0.8
2024.07.27
clubs/views/club_admin.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처
- 모임 관리자: 모임 기본 정보 수정, 모임 삭제, 멤버 초대, 멤버 삭제, 관리자로 등록/삭제
'''
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission

from django.db import transaction
from django.http import Http404

from utils.compress_image import compress_image
from .club_common import ClubViewSet, IsClubAdmin, IsMemberOfClub
from ..models import ClubMember, User
from ..serializers import ClubSerializer
from .club_common import IsMemberOfClub, ClubViewSet
from ..models import Club, ClubMember, User
from ..serializers import ClubMemberSerializer, ClubSerializer
from utils.error_handlers import handle_club_400_invalid_serializer, handle_404_not_found, handle_400_bad_request

import logging

logger = logging.getLogger(__name__)

class IsClubAdmin(IsMemberOfClub):
    '''
    사용자가 모임 내에서 관리자 역할을 하는지 확인하는 권한 클래스
    '''
    def has_object_permission(self, request, view, obj):
        # 먼저 사용자가 모임의 멤버인지 확인한 후 (IsMemberOfClub에서 상속받아 사용)
        if super().has_object_permission(request, view, obj):
            # 요청한 사용자가 모임의 관리자 역할을 하는지 추가로 확인
            return ClubMember.objects.filter(club=obj, user=request.user, role='admin', status_type='active').exists()
        return False

class ClubAdminViewSet(ClubViewSet):
    """
    관리자 전용 기능: 클럽 수정(PATCH), 삭제, 멤버 초대, 삭제, 역할 변경 등.
    기본 ClubViewSet에서 상속받지만, 관리자 작업은 별도의 @action으로 처리합니다.
    """
    # 관리자 전용 기능은 별도의 권한 설정
    def get_permissions(self):
        permission_classes = [IsAuthenticated, IsClubAdmin]
        return [permission() for permission in permission_classes]

    """
    모임 수정 메서드
    - 모임이름, 이미지, 모임 설명
    - 관리자 추가/삭제
    """

    def partial_update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)

        try:
            club = self.get_object()  # 수정할 클럽 객체 가져오기
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', kwargs.get("pk"))

        # 요청 데이터 전처리: form-data와 JSON 모두 처리 (모임 생성 시와 유사)
        data = self.process_request_data(request)
        print("Request Data:", request.data)
        print("Processed Data:", data)

        # form-data의 경우, admins 값은 문자열 리스트일 수 있으므로 정수로 변환
        admins_member_ids_raw = data.get('admins', [])
        print(f"form-data: {admins_member_ids_raw}")
        try:
            admins_member_ids = [int(x) for x in admins_member_ids_raw]
        except Exception as e:
            return handle_400_bad_request("Admins field must contain valid integer IDs")
        print(f"Converted club_member IDs: {admins_member_ids}")
        # admins 필드에 정수화된 리스트로 대입
        data['admins'] = admins_member_ids

        # 이미지 처리: 이미지가 있다면 압축 처리
        image = request.FILES.get('image', None)
        if image:
            try:
                compressed_image = compress_image(image, output_format="WEBP")
                data['image'] = compressed_image
            except Exception as e:
                logger.error("Image compression error: %s", str(e))
                return handle_400_bad_request("Image processing error.")

        # 클럽 기본 정보 업데이트 (name, description, image 등)
        serializer = self.get_serializer(club, data=data, partial=partial)
        if not serializer.is_valid():
            return handle_club_400_invalid_serializer(serializer)
        try:
            club = serializer.save()
        except Exception as e:
            logger.error("Error updating club info: %s", str(e))
            return handle_400_bad_request("Error updating club info.")

        # 전달된 admins (ClubMember pk 값 리스트)를 기반으로 역할 업데이트 진행
        new_admin_member_ids = data.get('admins', [])
        if new_admin_member_ids is not None:
            try:
                # 현재 클럽의 관리자 ClubMember pk 목록 조회
                current_admin_member_ids = list(
                    ClubMember.objects.filter(club=club, role='admin').values_list('id', flat=True)
                )
                print(f"current_admin_member_ids: {current_admin_member_ids}")
                # 만약 새로 전달된 관리자 목록과 기존 목록이 다르다면 업데이트 진행
                if set(new_admin_member_ids) != set(current_admin_member_ids):
                    # 새로 전달된 관리자에 대해: 해당 ClubMember가 존재하는지 확인 후 role을 'admin'으로 업데이트
                    for member_id in new_admin_member_ids:
                        if not ClubMember.objects.filter(club=club, id=member_id).exists():
                            return handle_404_not_found('Club Member', member_id)
                        club_member = ClubMember.objects.get(club=club, id=member_id)
                        if club_member.role != 'admin':
                            club_member.role = 'admin'
                            club_member.save()
                    # 기존 관리자 중 새 목록에 없는 ClubMember는 role을 'member'로 업데이트
                    for member_id in current_admin_member_ids:
                        if member_id not in new_admin_member_ids:
                            club_member = ClubMember.objects.filter(club=club, id=member_id).first()
                            if club_member:
                                club_member.role = 'member'
                                club_member.save()
            except Exception as e:
                logger.error("Error updating admin roles: %s", str(e))
                return handle_400_bad_request("Error updating admin roles.")

        read_serializer = ClubSerializer(club, context={'request': request})
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully updated',
            'data': read_serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 모임 삭제 메서드
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', kwargs.get("pk"))

        self.perform_destroy(instance) # 모임 객체 삭제
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 모임에 멤버 초대 메서드
    @action(detail=True, methods=['post'], url_path='invite', url_name='invite_member')
    def invite_member(self, request, pk=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        user_ids = request.data.get('user_ids')  # 유저 ID 리스트 받기
        if not user_ids or not isinstance(user_ids, list):  # 유효하지 않은 요청 검증
            return handle_400_bad_request('User IDs must be a valid list of integers')

        # TODO: 다른 api와는 다르게 모임 초대할 때에는 PK가 아니라 유저 아이디로 초대하고 있음. 통일이 필요

        # 존재하는 유저 필터링 (pk)
        existing_users = set(User.objects.filter(user_id__in=user_ids).values_list('id', flat=True))
        if not existing_users:  # 존재하는 유저가 없을 경우
            return handle_404_not_found('Users', user_ids)
        
        # 이미 가입된 유저 필터링
        existing_members = set(ClubMember.objects.filter(club=club, user_id__in=existing_users).values_list('id', flat=True))
        new_users = existing_users - existing_members  # 가입되지 않은 유저만 초대
        if not new_users:  # 이미 모두 가입된 경우
            return handle_400_bad_request('All users are already members of the club')

        # 신규 ClubMember 객체 생성 (Bulk Create 사용)
        # TODO: 향후, 초대받은 유저가 수락하는 기능도 만들 때, status_type = 'pending'으로 변경해야함
        new_members = [ClubMember(club=club, user_id=account_id, role='member', status_type='active') for account_id in new_users]
        with transaction.atomic():  # 트랜잭션 사용
            ClubMember.objects.bulk_create(new_members)

        # 새로 추가된 멤버를 user_id 기준으로 다시 조회 (select_related로 user 정보 포함)
        created_members = ClubMember.objects.filter(club=club, user_id__in=list(new_users)).select_related('user')

        # 생성된 ClubMember들을 시리얼라이즈
        serializer = ClubMemberSerializer(created_members, many=True, context={'request': request})
        response_data = {
            'status': status.HTTP_201_CREATED,
            'message': 'Members successfully invited',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    # 모임 내 특정 멤버 강제 삭제 메서드
    @action(detail=True, methods=['delete'], url_path=r'members/(?P<member_id>\d+)', url_name='remove_member')
    def remove_member(self, request, pk=None, member_id=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        member = ClubMember.objects.filter(club=club, id=member_id).first()

        if not member: # 사용자가 해당 모임의 멤버가 아닌 경우, 404 반환
            return handle_404_not_found('Club Member', member_id)

        member.delete() # 멤버 삭제

        return Response(status=status.HTTP_204_NO_CONTENT)

    # 모임 내 특정 멤버 역할 변경 메서드
    # TODO: admin, member로 요청하는게 더 간단함. 현재는 너무 억지로 A, M으로 바꾸고 있음 -> 이전에 대문자로 쓰자 했던건 admin을 대문자로 쓰자는거였음
    @action(detail=True, methods=['patch'], url_path=r'members/(?P<member_id>\d+)/role', url_name='update_role')
    def update_role(self, request, pk=None, member_id=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        role_type = request.query_params.get('role_type') # 쿼리 파라미터 데이터 가져오기

        if not role_type or role_type not in ['A', 'M']: # 유효하지 않은 데이터인 경우, 400 반환
            return handle_400_bad_request('Invalid role_type value. Please specify \'A\' for admin or \'M\' for member')

        member = ClubMember.objects.filter(club=club, id=member_id).first()

        if not member: # 사용자가 해당 모임의 멤버가 아닌 경우, 404 반환
            return handle_404_not_found('Club Member', member_id)

        member.role = 'admin' if role_type == 'A' else 'member' # 역할 변경
        member.save()
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Role updated successfully',
            'data': {
                'club_id': club.id,
                'member_id': member_id,
                'role': 'admin' if role_type == 'A' else 'member'
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    # 멤버 초대 수락 메서드
    @action(detail=True, methods=['patch'], url_path=r'members/(?P<member_id>\d+)/status', url_name='update_status')
    def update_status_type(self, request, pk=None, member_id=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        member = ClubMember.objects.filter(club=club, id=member_id).first()
        if not member: # 사용자가 해당 모임의 멤버가 아닌 경우, 404 반환
            return handle_404_not_found('Club Member', member_id)
    
        if member.status_type != 'pending': # 유효하지 않은 데이터인 경우, 400 반환
            return handle_400_bad_request('Invalid status_type(\'pending\') value.')

        member.status_type = 'active' # 역할 변경
        member.save()
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'status updated successfully',
            'data': {
                'club_id': club.id,
                'member_id': member_id,
                'status_type': member.status_type
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)