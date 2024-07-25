'''
MVP demo ver 0.0.8
2024.07.25
clubs/views.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
기능:
- Authorization Type: Bearer Token
- ModelViewSet을 이용하여 모임의 CRUD 기능 구현
- 모임: 생성, 조회, 특정 모임 조회, 특정 모임의 멤버 조회
- 모임 관리자: 모임 기본 정보 수정, 모임 삭제, 멤버 초대, 멤버 삭제, 관리자로 등록/삭제
- 모임 멤버: 모임 초대 수락/거절, 모임 나가기

누구나 모임을 생성하고, 자신이 속한 모임을 조회하고, 모임 초대 수락/거절 가능
관리자는 자신이 관리하는 모임의 정보 수정, 삭제, 멤버 초대, 삭제, 역할 변경 가능
'''
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.http import Http404

from .models import Club, ClubMember, User
from .serializers import ClubSerializer, ClubCreateUpdateSerializer, ClubMemberAddSerializer, ClubAdminAddSerializer, \
    ClubMemberSerializer

class ClubViewSet(viewsets.ModelViewSet):
    '''
    모임 관련 CRUD 클래스
    '''
    queryset            = Club.objects.all() # 모든 Club 객체 가져오기
    serializer_class    = ClubSerializer
    permission_classes  = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClubCreateUpdateSerializer
        return ClubSerializer

    '''
    모임
    '''
    # 모임 생성 메서드
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)  # 요청 데이터를 사용해 serializer 초기화
        if not serializer.is_valid():
            # 유효성 검사 실패 시 에러 메시지 반환
            errors = {
                "name": "Name field is required and must be a non-empty string" if "name" in serializer.errors else None,
                "description": "Description field must be a string" if "description" in serializer.errors else None,
                "image": "Image URL must be a valid URL" if "image" in serializer.errors else None,
                "members": "Members field must be a list of valid user IDs" if "members" in serializer.errors else None,
                "admin": "Admin field must be a list of valid user IDs, and at least one admin must be specified" if "admin" in serializer.errors else None,
            }
            return Response({
                "status": 400,
                "message": "Invalid request payload",
                "errors": {k: v for k, v in errors.items() if v is not None}
            }, status=status.HTTP_400_BAD_REQUEST)

        club = serializer.save()  # 유효한 데이터인 경우 모임 생성

        # 일반 멤버와 관리자 리스트
        members = request.data.get('members', [])
        admins = request.data.get('admins', [])

        # 관리자 또는 멤버가 리스트 타입이 아닌 경우, 400 반환
        if not isinstance(members, list) or not isinstance(admins, list):
            return Response({
                'status': 400,
                'message': 'Invalid request payload',
                'errors': {'members': 'Members field must be a list of valid user IDs',
                           'admin': 'Admin field must be a list of valid user IDs'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # 관리자 필드가 비어있는 경우, 400 반환
        if not admins:
            return Response({
                'status': 400,
                'message': 'Admin field must be a list of valid user IDs, and at least one admin must be specified'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 중복된 멤버나 관리자가 추가되지 않도록 중복 여부 확인 (관리자 우선 추가)
        for admin_id in admins:
            if not User.objects.filter(id=admin_id).exists(): # 사용자가 존재하지 않는 경우 404 반환
                return Response({
                    'status': 404,
                    'message': f'User {admin_id} is not found'
                }, status=status.HTTP_404_NOT_FOUND)
            if ClubMember.objects.filter(club=club, user_id=admin_id).exists():
                continue  # 중복 관리자는 추가하지 않음
            ClubMember.objects.create(club=club, user_id=admin_id, role='admin')


        for member_id in members:
            if not User.objects.filter(id=member_id).exists(): # 사용자가 존재하지 않는 경우 404 반환
                return Response({
                    'status': 404,
                    'message': f'User {member_id} is not found'
                }, status=status.HTTP_404_NOT_FOUND)
            if ClubMember.objects.filter(club=club, user_id=member_id).exists():
                continue  # 중복 멤버는 추가하지 않음 (또는 이미 관리자로 추가되어 있는 경우)
            ClubMember.objects.create(club=club, user_id=member_id, role='member')


        read_serializer = ClubSerializer(club)
        response_data   = {
            'code': status.HTTP_201_CREATED,
            'message': 'successfully Club created',
            'data': read_serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    # 특정 모임 조회 메서드
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object() # 조회할 모임 객체
        except Http404: # 모임이 존재하지 않는 경우
            return Response({
                'status': 404,
                'message': f'Club {kwargs.get("pk")} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer      = self.get_serializer(instance) # 모임 객체 직렬화
        response_data   = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 멤버리스트 조회 메서드
    @action(detail=True, methods=['get'], url_path='members', url_name='members')
    def retrieve_members(self, request, pk=None):
        try:
            club = self.get_object() # 조회할 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Club {pk} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        members = ClubMember.objects.filter(club=club) # 해당 모임의 모든 멤버 저장
        serializer = ClubMemberSerializer(members, many=True) # 멤버 리스트 직렬화
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved members',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    '''
    모임 관리자
    '''
    # 모임 기본 정보 수정 메서드
    def partial_update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)

        try:
            instance = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Club {kwargs.get("pk")} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if not serializer.is_valid(): # 유효하지 않은 데이터가 들어온 경우, 400 반환
            errors = {
                "name": "Name field is required and must be a non-empty string" if "name" in serializer.errors else None,
                "description": "Description field must be a string" if "description" in serializer.errors else None,
                "image": "Image URL must be a valid URL" if "image" in serializer.errors else None,
            }
            return Response({
                "status": 400,
                "message": "Invalid request payload",
                "errors": {k: v for k, v in errors.items() if v is not None}
            }, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({
                'status': 404,
                'message': f'Club {kwargs.get("pk")} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        self.perform_destroy(instance) # 모임 객체 삭제
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 모임에 멤버 초대 메서드
    @action(detail=True, methods=['post'], url_path='invite', url_name='invite_member')
    def invite_member(self, request, pk=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Club {pk} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user_id')
        if not user_id: # 유효하지 않은 user_id인 경우, 400 반환
            return Response({
                'status': 400,
                'message': 'Invalid request payload',
                'errors': {'user_id': 'User ID is required and must be a valid integer'}
            }, status=status.HTTP_400_BAD_REQUEST)

        if not User.objects.filter(id=user_id).exists():  # 사용자가 존재하지 않을 경우, 404 반환
            return Response({
                'status': 404,
                'message':  f'User {user_id} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        if ClubMember.objects.filter(club=club, user_id=user_id).exists(): # 사용자가 이미 모임에 존재하는 경우, 400 반환
            return Response({
                'status': 400,
                'message': f'User {user_id} is already a member of the club'
            }, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({
                'status': 404,
                'message': f'Club {pk} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        member = ClubMember.objects.filter(club=club, user_id=member_id).first()

        if not member: # 사용자가 해당 모임의 멤버가 아닌 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Member {member_id} is not found in Club {club.id}'
            }, status=status.HTTP_404_NOT_FOUND)

        member.delete() # 멤버 삭제

        return Response(status=status.HTTP_204_NO_CONTENT)

    # 모임 내 특정 멤버 역할 변경 메서드
    @action(detail=True, methods=['patch'], url_path=r'members/(?P<member_id>\d+)/role', url_name='update_role')
    def update_role(self, request, pk=None, member_id=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Club {pk} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        role_type = request.query_params.get('role_type') # 쿼리 파라미터 데이터 가져오기

        if not role_type or role_type not in ['A', 'M']: # 유효하지 않은 데이터인 경우, 400 반환
            return Response({
                'status': 400,
                'message': 'Invalid role_type value. Please specify \'A\' for admin or \'M\' for member'
            }, status=status.HTTP_400_BAD_REQUEST)

        member = ClubMember.objects.filter(club=club, user_id=member_id).first()

        if not member: # 사용자가 해당 모임의 멤버가 아닌 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Member {member_id} is not found in Club {club.id}'
            }, status=status.HTTP_404_NOT_FOUND)

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

    '''
    모임 멤버
    '''
    # 초대 받은 멤버가 참여 수락/거절하는 메서드
    @action(detail=True, methods=['post'], url_path='join', url_name='join_club')
    def join_club(self, request, pk=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Club {pk} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        user = request.user # JWT 토큰을 통해 인증된 사용자 정보를 가져옴
        status_choice = request.data.get('status')

        if status_choice not in ['accepted', 'declined']: # 유효하지 않은 데이터인 경우, 400 반환
            return Response({
                'status': 400,
                'message': 'status is required. Please specify \'accepted\' or \'declined\''
            }, status=status.HTTP_400_BAD_REQUEST)

        member = ClubMember.objects.filter(club=club, user=user).first()

        if not member: # 사용자가 해당 모임의 멤버가 아닌 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Member {user.id} is not found in Club {club.id}'
            }, status=status.HTTP_404_NOT_FOUND)

        if status_choice == 'accepted':
            member.role = 'member'
            member.save()
            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully joined the club',
                'data': {
                    'club_id': club.id,
                    'user_id': user.id,
                    'status': 'accepted'
                }
            }
        else:
            member.delete()
            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully declined the club invitation',
                'data': {
                    'club_id': club.id,
                    'user_id': user.id,
                    'status': 'declined'
                }
            }

        return Response(response_data, status=status.HTTP_200_OK)

    # 모임 나가기 메서드
    @action(detail=True, methods=['delete'], url_path='leave', url_name='leave_club')
    def leave_club(self, request, pk=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Club {pk} is not found'
            }, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        member = ClubMember.objects.filter(club=club, user=user).first()

        if not member:  # 사용자가 해당 클럽의 멤버가 아닌 경우, 404 반환
            return Response({
                'status': 404,
                'message': f'Member {user.id} is not found in Club {club.id}'
            }, status=status.HTTP_404_NOT_FOUND)

        member.delete() # 멤버 삭제

        return Response(status=status.HTTP_204_NO_CONTENT)