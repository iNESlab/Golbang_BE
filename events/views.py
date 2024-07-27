# events/views.py
from datetime import date, datetime

from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from clubs.models import ClubMember, Club
from participants.models import Participant
from .models import Event
from .serializers import EventCreateUpdateSerializer, EventDetailSerializer
from .utils import EventUtils


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()

    def get_serializer_class(self):
        if self.action in ['retrieve','partial_udpate']:
            return EventDetailSerializer
        elif self.action in ['update', 'partial_update']:
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
        user = self.request.user
        club_id = self.request.query_params.get('club_id')

        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({'status': status.HTTP_404_NOT_FOUND,'message': "club_id is not found"},
                            status=status.HTTP_404_NOT_FOUND)

        member = ClubMember.objects.get(user=user, club=club)
        if member is None or member.role != "admin":
            return Response({'status': status.HTTP_401_UNAUTHORIZED, 'message': "user is not a club_admin"},
                            status=status.HTTP_401_UNAUTHORIZED)

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
        user = self.request.user
        event_id = self.kwargs.get('pk')

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "event not found"}, status=status.HTTP_400_BAD_REQUEST)

        member = ClubMember.objects.get(user=user, club=event.club)
        if member is None or member.role != "admin":
            return Response({'status': status.HTTP_401_UNAUTHORIZED, 'message': "user is not a club_admin",},
                            status=status.HTTP_401_UNAUTHORIZED)

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
            return Response({"status": status.HTTP_400_BAD_REQUEST, "message": "event_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "event not found"},
                            status=status.HTTP_404_NOT_FOUND)

        participants = Participant.objects.filter(event=event, club_member__user=user)
        if not participants.exists():
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
            return Response({"status": status.HTTP_400_BAD_REQUEST,
                             "message": "date(YYYY-MM-DD) 형식을 지켜주세요."},
                            status=status.HTTP_400_BAD_REQUEST)

        status_type = request.query_params.get('status_type')
        if status_type not in [None, Participant.StatusType.__members__]:
            return Response({"status": status.HTTP_400_BAD_REQUEST,
                             "message": "status_type(null or ACCEPT) 형식을 지켜주세요."},
                            status=status.HTTP_400_BAD_REQUEST)

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
        except Event.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "event not found"},
                            status=status.HTTP_404_NOT_FOUND)

        member = ClubMember.objects.get(user=user,club=event.club)

        if member is None or member.role != "admin":
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "event not found"},
                            status=status.HTTP_404_NOT_FOUND)

        self.perform_destroy(event)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()
