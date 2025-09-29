'''
MVP demo ver 0.0.9
2024.10.22
clubs/views/club_common.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
기능:
- Authorization Type: Bearer Token
- ModelViewSet을 이용하여 모임의 CRUD 기능 구현
- 모임: 생성, 조회, 특정 모임 조회, 특정 모임의 멤버 조회
누구나 모임을 생성하고, 자신이 속한 모임을 조회하고, 모임 초대 수락/거절 가능
'''
from sympy import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.http import Http404, QueryDict
import logging

from utils.compress_image import compress_image
from ..models import Club, ClubMember, User
from ..serializers import (ClubSerializer, ClubCreateUpdateSerializer, ClubMemberAddSerializer, ClubAdminAddSerializer,
                           ClubMemberSerializer) # TODO: 안 쓰는 건 제거
from clubs.tasks import send_club_creation_notification
from events.models import Event

from utils.error_handlers import handle_club_400_invalid_serializer, handle_404_not_found, handle_400_bad_request

logger = logging.getLogger(__name__)

class IsMemberOfClub(BasePermission):
    '''
    사용자가 모임에 속한 멤버인지 확인하는 권한 클래스
    '''

    # TODO: has_permission, has_object_permission 이 꼭 나뉘어져야 하는가
    def has_permission(self, request, view):
        # 요청한 사용자가 어떤 모임의 멤버인지 확인 (뷰 수준, 리스트 뷰, 생성 뷰에 사용)
        # ex. 모임 목록 보기
        # 🔧 수정: 거절됨을 제외한 모든 상태의 멤버가 클럽 목록을 볼 수 있도록 허용
        return ClubMember.objects.filter(
            user=request.user
        ).exclude(
            status_type='rejected'
        ).exists()

    def has_object_permission(self, request, view, obj):
        # 🔧 수정: 거절됨을 제외한 모든 상태의 멤버가 클럽 정보를 볼 수 있도록 허용
        # ex. 특정 모임 정보 보기 (초대됨, 신청함, 가입됨 모두 허용)
        return ClubMember.objects.filter(
            club=obj, 
            user=request.user
        ).exclude(
            status_type='rejected'
        ).exists()

# class IsClubAdmin(BasePermission):
#     '''
#     사용자가 모임 내에서 관리자 역할을 하는지 확인하는 권한 클래스
#     '''
#     def has_object_permission(self, request, view, obj):
#         # 먼저 사용자가 모임의 멤버인지 확인한 후 (IsMemberOfClub에서 상속받아 사용)
#         if super().has_object_permission(request, view, obj):
#             # 요청한 사용자가 모임의 관리자 역할을 하는지 추가로 확인
#             return ClubMember.objects.filter(club=obj, user=request.user, role='admin').exists()
#         return False

class IsClubAdmin(BasePermission):
    """
    모임(Club) 또는 이벤트(Event)가 넘어올 때 모두 사용자가 모임 내에서 '관리자' 역할을 가지는지 확인하는 클래스
    """
    def has_object_permission(self, request, view, obj):
        # 1) obj가 Event 인스턴스면 실제 모임은 obj.club
        if isinstance(obj, Event):
            club = obj.club
        else:
            club = obj  # Club 인스턴스인 경우

        # 2) 먼저 모임 멤버인지 확인 (IsMemberOfClub.super)
        if not super().has_object_permission(request, view, club):
            return False

        # 3) 멤버라면 role='admin' 인지 검사
        return ClubMember.objects.filter(
            club=club,
            user=request.user,
            role='admin'
        ).exists()

class ClubViewSet(viewsets.ModelViewSet):
    '''
    모임 관련 CRUD 기능 제공 클래스
    '''
    queryset            = Club.objects.all()                # 모든 Club 객체 가져오기
    serializer_class    = ClubSerializer                    # 기본으로 사용할 시리얼라이저 클래스 설정
    permission_classes  = [IsAuthenticated, IsMemberOfClub] # 기본 권한: 인증된 사용자이고, 모임의 멤버여야 함

    def get_permissions(self):
        # 액션에 따라 필요한 권한 설정
        permission_classes = [IsAuthenticated]  # 기본 권한: 인증된 사용자
        if self.action in ['retrieve', 'list']:
            # 모임을 조회하거나 목록을 볼 때는 모임의 멤버여야 함
            permission_classes.append(IsMemberOfClub)
        elif self.action in ['partial_update', 'destroy', 'invite_member', 'remove_member', 'update_role']:
            # 모임을 수정, 삭제하거나 멤버를 초대, 삭제, 관리자로 등록/삭제할 때는 모임의 관리자여야 함
            permission_classes.extend([IsMemberOfClub, IsClubAdmin])
        self.permission_classes = permission_classes
        return super().get_permissions()

    def get_queryset(self): # 데이터베이스로부터 가져온 객체 목록
        user = self.request.user
        # 🔧 수정: 거절됨을 제외한 모든 상태의 클럽 반환 (초대됨, 신청함, 가입됨)
        return Club.objects.filter(
            clubmember__user=user
        ).exclude(
            clubmember__status_type='rejected'
        ).distinct()


    '''
    모임 공통 기능
    '''

    def process_request_data(self, request):
        """ 요청 데이터를 적절한 형식으로 변환하여 반환 """
        if isinstance(request.data, QueryDict):
            data = dict(request.data)
            data['name'] = request.data.get('name')
            data['description'] = request.data.get('description')
            data['image'] = request.data.get('image')

            # members와 admins를 쉼표로 구분된 문자열로 받음
            members_str = request.data.get('members', '')
            admins_str = request.data.get('admins', '')

            # 쉼표로 구분된 문자열을 리스트로 변환 (userId가 들어오므로 나중에 id로 변환 필요)
            data['members'] = [member.strip() for member in members_str.split(',') if member.strip()]
            data['admins'] = [admin.strip() for admin in admins_str.split(',') if admin.strip()]
            print("Processed Data1:", data)
        else:
            data = request.data.copy()
            data['members'] = [member for member in request.data.get('members', [])]
            data['admins'] = [admin for admin in request.data.get('admins', [])]
            print("Processed Data2:", data)
        return data

    # 모임 생성 메서드
    def create(self, request, *args, **kwargs):
        ## Club
        # 데이터 복사 및 JSON 요청과 form-data 요청을 구분하여 처리
        data = self.process_request_data(request)
        print("Request Data:", request.data)
        print("Processed Data:", data)

        # 프론트에서 받은 userId 리스트로 유저 검색 후, 그 id를 members 및 admins에 저장
        members_user_ids = data.get('members', [])
        admins_user_ids = data.get('admins', [])

        # 유효한 유저인지 확인하고, userId로 User 모델에서 검색하여 id로 변환
        members = User.objects.filter(user_id__in=members_user_ids)
        admins = User.objects.filter(user_id__in=admins_user_ids)

        # userId가 유효하지 않은 경우 처리
        if members.count() != len(members_user_ids):
            return handle_400_bad_request('Invalid user IDs in members')
        if admins.count() != len(admins_user_ids):
            return handle_400_bad_request('Invalid user IDs in admins')

        # 각각의 user.id에 대응하는 {members/admins} id 리스트 생성
        members_ids = list(members.values_list('id', flat=True))
        admins_ids = list(admins.values_list('id', flat=True))

        # members와 admins 리스트를 id로 변경
        data['members'] = members_ids
        data['admins'] = admins_ids

        # 이미지 압축 적용
        image = request.FILES.get('image', None)
        if image:
            compressed_image = compress_image(image, output_format="WEBP")
            data['image'] = compressed_image  # 압축된 이미지로 데이터 변경

        serializer = self.get_serializer(data=data)  # 요청 데이터를 사용해 serializer 초기화

        if not serializer.is_valid():
            # 유효성 검사 실패 시 에러 메시지 반환
            return handle_club_400_invalid_serializer(serializer)


        club = serializer.save()  # 유효한 데이터인 경우 모임 생성

        # 🔧 추가: 모임 생성 시 채팅방 자동 생성
        from chat.models import ChatRoom, ChatMessage
        try:
            chat_room, created = ChatRoom.objects.get_or_create(
                chat_room_type='CLUB',
                club_id=club.id,
                defaults={
                    'chat_room_name': f'{club.name} 채팅방',
                    'is_active': True
                }
            )
            if created:
                print(f"✅ 모임 채팅방 자동 생성 완료: {chat_room.chat_room_name} (ID: {chat_room.id})")
                
                # 🔧 추가: 채팅방 생성 시 시스템 메시지 자동 전송 (주석처리 - sender_name 오류)
                # try:
                #     system_message = ChatMessage.objects.create(
                #         chat_room=chat_room,
                #         sender_id=0,  # 시스템 메시지
                #         sender_name='시스템',
                #         content=f'🎉 {club.name} 모임이 생성되었습니다!',
                #         message_type='SYSTEM',
                #         is_read=False
                #     )
                #     print(f"✅ 시스템 메시지 생성 완료: {system_message.content}")
                # except Exception as e:
                #     print(f"❌ 시스템 메시지 생성 실패: {e}")
            else:
                print(f"ℹ️ 모임 채팅방이 이미 존재합니다: {chat_room.chat_room_name} (ID: {chat_room.id})")
        except Exception as e:
            print(f"❌ 모임 채팅방 생성 실패: {e}")

        # 🎵 추가: 모임 생성 시 기본 이벤트 자동 생성 (라디오 방송용)
        from events.models import Event
        from django.utils import timezone
        from datetime import timedelta
        try:
            # 현재 시간부터 24시간 후까지의 기본 이벤트 생성
            now = timezone.now()
            default_event = Event.objects.create(
                club=club,
                event_title=f'{club.name} 기본 이벤트',
                location='0,0',  # 기본 위치
                site='기본 장소',
                start_date_time=now,  # 지금부터 시작
                end_date_time=now + timedelta(days=1),  # 24시간 후 종료
                repeat_type='NONE',
                game_mode='SP'
            )
            print(f"✅ 모임 기본 이벤트 자동 생성 완료: {default_event.event_title} (ID: {default_event.id})")
        except Exception as e:
            print(f"❌ 모임 기본 이벤트 생성 실패: {e}")

        ## ClubMember
        # 일반 멤버와 관리자 리스트
        members = data.get('members', [])
        admins = data.get('admins', [])

        # 관리자 또는 멤버가 리스트 타입이 아닌 경우, 400 반환
        if not isinstance(members, list) or not isinstance(admins, list):
            return handle_400_bad_request('Members and admins fields must be list types of valid user IDs')

        # 관리자 필드가 비어있는 경우, 400 반환
        if not admins:
            return handle_400_bad_request('Admins field must be a list of valid user IDs, and at least one admin must be specified')

        # 중복된 멤버나 관리자가 추가되지 않도록 중복 여부 확인 (관리자 우선 추가)
        for admin_id in admins:
            if not User.objects.filter(id=admin_id).exists(): # 사용자가 존재하지 않는 경우 404 반환
                return handle_404_not_found('User', admin_id)

            if ClubMember.objects.filter(club=club, user_id=admin_id).exists():
                continue  # 중복 관리자는 추가하지 않음
            ClubMember.objects.create(club=club, user_id=admin_id, role='admin', status_type='active')


        for member_id in members:
            if not User.objects.filter(id=member_id).exists(): # 사용자가 존재하지 않는 경우 404 반환
                return handle_404_not_found('User', member_id)

            if ClubMember.objects.filter(club=club, user_id=member_id).exists():
                continue  # 중복 멤버는 추가하지 않음 (또는 이미 관리자로 추가되어 있는 경우)
            ClubMember.objects.create(club=club, user_id=member_id, role='member', status_type='invited')

        # 응답 반환 후 비동기적으로 FCM 알림 전송
        send_club_creation_notification.delay(club.id)

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
            return handle_404_not_found('Club', kwargs.get("pk"))

        serializer      = self.get_serializer(instance) # 모임 객체 직렬화
        response_data   = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    # 모임 검색 API
    @action(detail=False, methods=['get'], url_path='search', url_name='search_clubs')
    def search_clubs(self, request):
        query = request.query_params.get('club_name', '').strip()

        if not query:
            return Response({
                'status': status.HTTP_400_BAD_REQUEST,
                'message': '검색어(club_name)를 입력해주세요.',
                'data': []
            }, status=status.HTTP_400_BAD_REQUEST)

        # name / description 기준으로 검색
        clubs = Club.objects.filter(name__icontains=query)[:50]  # TODO: 모임이 많아지면, 페이징 필요

        serializer = ClubSerializer(clubs, many=True, context={'request': request})
        return Response({
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved search results',
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    # 멤버리스트 조회 메서드
    @action(detail=True, methods=['get'], url_path='members', url_name='members')
    def retrieve_members(self, request, pk=None):
        try:
            club = self.get_object() # 조회할 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        members = ClubMember.objects.filter(club=club) # 해당 모임의 모든 멤버 조회, 초대 수락 전도 포함
        serializer = ClubMemberSerializer(members, many=True, context={'request': request}) # 멤버 리스트 직렬화
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved members',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    # 🔧 추가: 모임 가입 신청 API
    @action(detail=True, methods=['post'], url_path='apply')
    def apply_club(self, request, pk=None):
        """
        사용자가 클럽에 가입 신청하는 API
        """
        try:
            # 🔧 수정: apply_club에서는 모든 클럽에 접근 가능해야 함
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return handle_404_not_found('Club', pk)

        user = request.user

        # 이미 멤버인지 확인
        existing_member = ClubMember.objects.filter(club=club, user=user).first()
        if existing_member:
            if existing_member.status_type == 'active':
                return Response({
                    'status': status.HTTP_400_BAD_REQUEST,
                    'message': '이미 클럽의 활성 멤버입니다.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)
            elif existing_member.status_type == 'applied':
                return Response({
                    'status': status.HTTP_400_BAD_REQUEST,
                    'message': '이미 가입 신청이 진행 중입니다.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)
            elif existing_member.status_type == 'invited':
                return Response({
                    'status': status.HTTP_400_BAD_REQUEST,
                    'message': '이미 초대받은 상태입니다. 초대를 수락해주세요.',
                    'data': {}
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # 기존 멤버가 있으면 상태를 'applied'로 변경
                existing_member.status_type = 'applied'
                existing_member.save()
        else:
            # 새로운 멤버 생성
            ClubMember.objects.create(
                club=club,
                user=user,
                role='member',
                status_type='applied'
            )

        # 🔧 추가: 가입 신청 알림 전송
        try:
            from utils.push_fcm_notification import send_club_application_notification
            send_club_application_notification(club, user)
        except Exception as e:
            logger.error(f"가입 신청 알림 전송 실패: {e}")

        return Response({
            'status': status.HTTP_201_CREATED,
            'message': '가입 신청이 완료되었습니다. 관리자의 승인을 기다려주세요.',
            'data': {
                'club_id': club.id,
                'user_id': user.id,
                'status_type': 'applied',
                'action': 'application_submitted'
            }
        }, status=status.HTTP_201_CREATED)

    # 🔧 추가: 초대 수락/거절 API (사용자용)
    @action(detail=True, methods=['post'], url_path='respond-invitation')
    def respond_invitation(self, request, pk=None):
        """
        사용자가 초대에 응답하는 API (수락/거절)
        """
        try:
            club = self.get_object()
        except Http404:
            return handle_404_not_found('Club', pk)

        user = request.user
        response_type = request.data.get('response')  # 'accepted' or 'declined'

        if response_type not in ['accepted', 'declined']:
            return handle_400_bad_request('response는 "accepted" 또는 "declined"이어야 합니다.')

        try:
            member = ClubMember.objects.get(club=club, user=user, status_type='invited')
            
            if response_type == 'accepted':
                member.status_type = 'active'
                member.save()
                
                return Response({
                    'status': status.HTTP_200_OK,
                    'message': '초대를 수락했습니다. 클럽에 가입되었습니다.',
                    'data': {
                        'club_id': club.id,
                        'user_id': user.id,
                        'status_type': 'active',
                        'action': 'invitation_accepted'
                    }
                }, status=status.HTTP_200_OK)
            else:
                member.delete()
                
                return Response({
                    'status': status.HTTP_200_OK,
                    'message': '초대를 거절했습니다.',
                    'data': {
                        'club_id': club.id,
                        'user_id': user.id,
                        'action': 'invitation_declined'
                    }
                }, status=status.HTTP_200_OK)
                
        except ClubMember.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': '초대를 찾을 수 없습니다.',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)

    # 🔧 추가: 신청 취소 API
    @action(detail=True, methods=['post'], url_path='cancel-application')
    def cancel_application(self, request, pk=None):
        """
        사용자가 가입 신청을 취소하는 API
        """
        try:
            # 🔧 수정: cancel_application에서는 모든 클럽에 접근 가능해야 함
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return handle_404_not_found('Club', pk)

        user = request.user

        # 신청 상태인 멤버 찾기
        try:
            member = ClubMember.objects.get(club=club, user=user, status_type='applied')
        except ClubMember.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': '신청 내역을 찾을 수 없습니다.',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)

        # 신청 취소 (멤버 삭제)
        member.delete()

        return Response({
            'status': status.HTTP_200_OK,
            'message': '신청이 취소되었습니다.',
            'data': {
                'club_id': club.id,
                'club_name': club.name,
                'action': 'application_cancelled'
            }
        }, status=status.HTTP_200_OK)
