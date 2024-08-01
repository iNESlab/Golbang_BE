# events/views.py
from datetime import date, datetime

from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from clubs.models import ClubMember, Club
from clubs.views.club_common import IsClubAdmin, IsMemberOfClub
from participants.models import Participant
from events.models import Event
from events.serializers import EventCreateUpdateSerializer, EventDetailSerializer
from events.utils import EventUtils
from utils.error_handlers import handle_404_not_found, handle_400_bad_request


@permission_classes([IsAuthenticated])
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    permission_classes = [IsAuthenticated]  # 기본 권한: 인증된 사용자이고, 모임의 멤버여야 함

    def get_permissions(self):
        # 조회 액션은 로그인한 유저라면 누구나 접근 가능
        self.permission_classes = [IsAuthenticated]
        # 나머지 액션은 관리자만 접근 가능
        if self.action not in ['retrieve', 'list']:
            self.permission_classes.append(IsClubAdmin)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['retrieve','list']:
            return EventDetailSerializer
        elif self.action in ['create', 'update']:
            return EventCreateUpdateSerializer
        return EventCreateUpdateSerializer

    # 이벤트 생성 메서드
    def create(self, request, *args, **kwargs):
        # TODO: 참가자 중복 검사 추가. 근데, 개발중에는 빠른 확인을 위해 중복 허용하겠습니다!
        """
        Post 요청 시 이벤트(Event) 생성
        요청 데이터: Event 정보 ('club_id', 'member_id', 'participants', 'event_title', 'location',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time')
        응답 데이터: Event 정보 (Event ID, 생성자 ID, 참가자 리스트, 제목, 장소, 시작/종료 시간, 반복 타입, 게임 모드, 알람 시간)
        """
        club_id = self.request.query_params.get('club_id')

        try:
            club = Club.objects.get(id=club_id)
            self.check_object_permissions(request, club)
        except Club.DoesNotExist:
            return handle_404_not_found('club', club_id)

        data = request.data.copy()
        data['club_id'] = club.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_data = {
            'code': status.HTTP_201_CREATED,
            'message': 'successfully Event created',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # TODO: 참가자 중복 검사 추가. 근데, 개발중에는 빠른 확인을 위해 중복 허용하겠습니다!
        event_id = self.kwargs.get('pk')

        try:
            event = Event.objects.get(pk=event_id)
            self.check_object_permissions(request, event.club)
        except Event.DoesNotExist:
            return handle_404_not_found('event', event_id)

        serializer = self.get_serializer(event, data=request.data, partial=True)  # 여기서 partial=True
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully updated',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 이벤트 조회 메서드
    def retrieve(self, request, *args, **kwargs):
        """
        GET 요청 시 특정 이벤트(Event) 정보 반환
        요청 데이터: Event ID
        응답 데이터: Event 정보 (Event ID, 생성자 ID, 참가자 리스트, 제목, 장소, 시작/종료 시간, 반복 타입, 게임 모드, 알람 시간)
        """
        user = request.user
        event_id = self.kwargs.get('pk')

        if not event_id:
            return handle_400_bad_request("event id is required")

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return handle_404_not_found('event', event_id)

        participants = Participant.objects.filter(event=event, club_member__user=user)
        if not (participants.exists() or ClubMember.objects.get(user=user, club=event.club).role == "admin"):
            return Response({"status": status.HTTP_401_UNAUTHORIZED, "message": "user is not invited"},
                            status=status.HTTP_401_UNAUTHORIZED)

        # Set group_type in context if needed
        context = super().get_serializer_context()
        context['group_type'] = participants.first().group_type

        instance = self.get_object()
        serializer = self.get_serializer(instance, context=context)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 이벤트 리스트 조회
    def list(self, request, *args, **kwargs):
        """
        GET 요청 시 해당 달 이벤트 목록(Events) 정보 반환
        요청 데이터: YYYY-MM-DD
        응답 데이터: Event (retrieve와 동일) 리스트
        """
        user = self.request.user

        date_str = request.query_params.get('date')
        if not date_str:
            date_str = str(date.today())

        try:
            # 날짜 문자열을 파싱하여 datetime 객체로 변환
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
        except ValueError:
            return handle_400_bad_request("date(YYYY-MM-DD) 형식을 지켜주세요.")

        status_type = request.query_params.get('status_type')
        if not (status_type is None or status_type in Participant.StatusType.__members__):
            return handle_400_bad_request("status_type(null or ACCEPT) 형식을 지켜주세요.")

        queryset = EventUtils.get_month_events_queryset(year, month, status_type, user)
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully event list',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

# 이벤트 삭제 메서드 (DELETE)
    def destroy(self, request, *args, **kwargs):
        user = request.user
        event_id = self.kwargs.get('pk')

        try:
            event = Event.objects.get(pk=event_id)
            self.check_object_permissions(request, event.club)
        except Event.DoesNotExist:
            return handle_404_not_found('event',event_id)

        member = ClubMember.objects.get(user=user,club=event.club)

        self.perform_destroy(event)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()
