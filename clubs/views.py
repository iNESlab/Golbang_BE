'''
MVP demo ver 0.0.7
2024.07.24
clubs/views.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
기능:
- Authorization Type: Bearer Token
- ModelViewSet을 이용하여 모임의 CRUD 기능 구현
- 모임: 생성, 조회, 특정 모임 조회, 특정 모임의 멤버 조회
- 모임 관리자: 모임 기본 정보 수정, 모임 삭제, 멤버 초대, 멤버 삭제, 관리자로 등록/삭제
- 모임 멤버: 모임 초대 수락/거절, 모임 나가기
'''
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Club, ClubMember, User
from .serializers import ClubSerializer, ClubCreateUpdateSerializer, ClubMemberAddSerializer, ClubAdminAddSerializer, \
    ClubMemberSerializer

class ClubViewSet(viewsets.ModelViewSet):
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
        '''
        POST 요청 시 모임(Club) 생성
        요청 데이터: 모임명, 설명, 이미지, 멤버, (모임) 관리자
        응답 데이터: 모임 정보 (club ID, 이름, 설명, 이미지, 멤버, 관리자, 생성일)
        '''
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club            = serializer.save()

        # 일반 멤버와 관리자
        members = request.data.get('members', [])
        admins = request.data.get('admins', [])

        for member_id in members:
            ClubMember.objects.create(club=club, user_id=member_id, role='member')

        for admin_id in admins:
            ClubMember.objects.create(club=club, user_id=admin_id, role='admin')

        read_serializer = ClubSerializer(club)
        response_data   = {
            'code': status.HTTP_201_CREATED,
            'message': 'successfully Club created',
            'data': read_serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    # 특정 모임 조회 메서드
    def retrieve(self, request, *args, **kwargs):
        """
        GET 요청 시 특정 모임(Club) 정보 반환
        요청 데이터: 모임 ID
        응답 데이터: 모임 정보 (ID, 이름, 설명, 이미지, 멤버, 관리자, 생성일)
        """
        instance    = self.get_object()
        serializer  = self.get_serializer(instance)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 멤버리스트 조회 메서드
    @action(detail=True, methods=['get'], url_path='members', url_name='members')
    def retrieve_members(self, request, pk=None):
        """
        GET 요청 시 특정 모임의 멤버 리스트 반환
        요청 데이터: 모임 ID
        응답 데이터: 멤버 리스트 (멤버 ID, 이름, 이메일, 역할)
        """
        club = self.get_object()
        members = ClubMember.objects.filter(club=club)
        serializer = ClubMemberSerializer(members, many=True)
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
        """
        PATCH 요청 시 모임의 기본 정보를 수정
        요청 데이터: 모임 정보 (이름, 설명, 이미지)
        응답 데이터: 수정된 모임 정보 (ID, 이름, 설명, 이미지, 수정일)
        """
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        club = serializer.save()
        read_serializer = ClubSerializer(club)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully updated',
            'data': read_serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 모임 삭제 메서드
    def destroy(self, request, *args, **kwargs):
        """
        DELETE 요청 시 모임 삭제
        요청 데이터: 모임 ID
        응답 데이터: 삭제 완료 메시지
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        response_data = {
            'status': status.HTTP_204_NO_CONTENT,
            'message': 'Successfully Deleted the Club'
        }
        return Response(response_data, status=status.HTTP_200_OK)  # No Content로 할 경우 아무것도 반환하지 않기 때문에 200으로 변경

    # 모임에 멤버 초대 메서드
    @action(detail=True, methods=['post'], url_path='invite', url_name='invite_member')
    def invite_member(self, request, pk=None):
        club = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': '유효하지 않은 데이터입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        if not User.objects.filter(id=user_id).exists():
            return Response({'detail': '해당 사용자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

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
        """
        DELETE 요청 시 특정 모임 내 특정 멤버 삭제
        요청 데이터: 없음
        응답 데이터: 삭제 완료 메시지
        """
        club = self.get_object()

        if not member_id:
            return Response({'detail': '유효하지 않은 데이터입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        member = ClubMember.objects.filter(club=club, user_id=member_id).first()
        if not member:
            return Response({'detail': '해당 멤버를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        member.delete()
        response_data = {
            'status': status.HTTP_204_NO_CONTENT,
            'message': 'Successfully Deleted the Member'
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 모임 내 특정 멤버 역할 변경 메서드
    @action(detail=True, methods=['patch'], url_path=r'members/(?P<member_id>\d+)/role', url_name='update_role')
    def update_role(self, request, pk=None, member_id=None):
        """
        PATCH 요청 시 모임 내 특정 멤버의 역할을 변경
        요청 데이터: role(admin/member)
        응답 데이터: 변경 완료 메시지
        """
        club = self.get_object()
        role = request.data.get('role')

        if not role or role not in ['member', 'admin']:
            return Response({'detail': '유효하지 않은 데이터입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        member = ClubMember.objects.filter(club=club, user_id=member_id).first()
        if not member:
            return Response({'detail': '해당 멤버를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        member.role = role
        member.save()
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Role updated successfully',
            'data': {
                'club_id': club.id,
                'member_id': member_id,
                'role': role
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)

    '''
    모임 멤버
    '''
    # 초대 받은 멤버가 참여 수락/거절하는 메서드
    @action(detail=True, methods=['post'], url_path='join', url_name='join_club')
    def join_club(self, request, pk=None):
        club = self.get_object()
        user = request.user
        status_choice = request.data.get('status')

        if status_choice not in ['accepted', 'declined']:
            return Response({'detail': '유효하지 않은 데이터입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        member = ClubMember.objects.filter(club=club, user=user).first()

        if not member:
            return Response({'detail': '초대를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

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
        """
        DELETE 요청 시 특정 모임 나가기
        요청 데이터: 없음
        응답 데이터: 나가기 완료 메시지
        """
        club = self.get_object()
        user = request.user
        member = ClubMember.objects.filter(club=club, user=user).first()

        if not member:
            return Response({'detail': '해당 멤버를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        member.delete()
        response_data = {
            'status': status.HTTP_204_NO_CONTENT,
            'message': 'Successfully left the club',
        }
        return Response(response_data, status=status.HTTP_200_OK)