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
from rest_framework.permissions import IsAuthenticated

from django.http import Http404

from .club_common import IsMemberOfClub, ClubViewSet
from ..models import Club, ClubMember, User
from ..serializers import ClubSerializer
from utils.error_handlers import handle_club_400_invalid_serializer, handle_404_not_found, handle_400_bad_request
#
# class IsClubAdmin(IsMemberOfClub):
#     '''
#     사용자가 모임 내에서 관리자 역할을 하는지 확인하는 권한 클래스
#     '''
#     def has_object_permission(self, request, view, obj):
#         # 먼저 사용자가 모임의 멤버인지 확인한 후 (IsMemberOfClub에서 상속받아 사용)
#         if super().has_object_permission(request, view, obj):
#             # 요청한 사용자가 모임의 관리자 역할을 하는지 추가로 확인
#             return ClubMember.objects.filter(club=obj, user=request.user, role='admin').exists()
#         return False

class ClubAdminViewSet(ClubViewSet):
    '''
    모임 내 관리자 기능 제공 클래스
    '''
    # def get_queryset(self): # 데이터베이스로부터 가져온 객체 목록
    #     user = self.request.user
    #     # 현재 요청한 사용자가 속한 모임만 반환
    #     return Club.objects.filter(members=user)

    # def get_permissions(self):
    #     # 액션에 따라 필요한 권한 설정
    #     permission_classes = [IsAuthenticated]  # 기본 권한: 인증된 사용자
    #     if self.action in ['partial_update', 'destroy', 'invite_member', 'remove_member', 'update_role']:
    #         # 모임을 수정, 삭제하거나 멤버를 초대, 삭제, 관리자로 등록/삭제할 때는 모임의 관리자여야 함
    #         permission_classes.extend([IsMemberOfClub, IsClubAdmin])
    #     self.permission_classes = permission_classes
    #     return super().get_permissions()

    # 모임 기본 정보 수정 메서드
    def partial_update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)

        try:
            instance = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', kwargs.get("pk"))

        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid(): # 유효하지 않은 데이터가 들어온 경우, 400 반환
            return handle_club_400_invalid_serializer(serializer)

        club = serializer.save()                # 유훃한 데이터인 경우 정보 업데이트
        read_serializer = ClubSerializer(club)  # 업데이트된 모임 데이터 직렬화
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

        user_id = request.data.get('user_id')
        if not user_id: # 유효하지 않은 user_id인 경우, 400 반환
            return handle_400_bad_request('User ID is required and must be a valid integer')

        if not User.objects.filter(id=user_id).exists():  # 사용자가 존재하지 않을 경우, 404 반환
            return handle_404_not_found('User', user_id)

        if ClubMember.objects.filter(club=club, user_id=user_id).exists(): # 사용자가 이미 모임에 존재하는 경우, 400 반환
            return handle_400_bad_request(f'User {user_id} is already a member of the club')

        # 새로운 멤버 추가
        ClubMember.objects.create(club=club, user_id=user_id, role='member')
        response_data = {
            'status': status.HTTP_201_CREATED,
            'message': 'Member successfully invited',
            'data': {
                'club_id': club.id,
                'user_id': user_id,
                'status': 'pending'
            }
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    # 모임 내 특정 멤버 강제 삭제 메서드
    @action(detail=True, methods=['delete'], url_path=r'members/(?P<member_id>\d+)', url_name='remove_member')
    def remove_member(self, request, pk=None, member_id=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        member = ClubMember.objects.filter(club=club, user_id=member_id).first()

        if not member: # 사용자가 해당 모임의 멤버가 아닌 경우, 404 반환
            return handle_404_not_found('Club Member', member_id)

        member.delete() # 멤버 삭제

        return Response(status=status.HTTP_204_NO_CONTENT)

    # 모임 내 특정 멤버 역할 변경 메서드
    @action(detail=True, methods=['patch'], url_path=r'members/(?P<member_id>\d+)/role', url_name='update_role')
    def update_role(self, request, pk=None, member_id=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        role_type = request.query_params.get('role_type') # 쿼리 파라미터 데이터 가져오기

        if not role_type or role_type not in ['A', 'M']: # 유효하지 않은 데이터인 경우, 400 반환
            return handle_400_bad_request('Invalid role_type value. Please specify \'A\' for admin or \'M\' for member')

        member = ClubMember.objects.filter(club=club, user_id=member_id).first()

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