# events/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from clubMembers.models import ClubMember
from members.models import Member
from participants.models import Participant
from .models import Event
from .serializers import EventCreateSerializer, EventDetailSerializer
from .utils import EventUtils


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventDetailSerializer
        elif self.action == 'create':
            return EventCreateSerializer
        return EventCreateSerializer

    # 이벤트 생성 메서드
    def create(self, request, *args, **kwargs):
        """
        Post 요청 시 모(Event 생성)
        """
        club_member_id = self.request.query_params.get('club_member_id')

        if not club_member_id:
            response_data = {
                'status': status.HTTP_400_BAD_REQUEST,
                'message': "club_member_id is required",
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
        try:
            club_member = ClubMember.objects.get(pk=club_member_id)
        except ClubMember.DoesNotExist:
            response_data = {
                'status': status.HTTP_404_NOT_FOUND,
                'message': "club_member_id is not found",
            }
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data['club_member_id'] = club_member.pk

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_data = {
            'code': status.HTTP_201_CREATED,
            'message': 'successfully Event created',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    # 이벤트 조회 메서드
    def retrieve(self, request, *args, **kwargs):
        """
        GET 요청 시 특정 이벤트(Event) 정보 반환
        요청 데이터: Event ID
        응답 데이터: Event 정보 (Event ID, 생성자 ID, 참가자 리스트, 제목, 장소, 시작/종료 시간, 반복 타입, 게임 모드, 알람 시간)
        """
        member_id = request.query_params.get('member_id')
        event_id = self.kwargs.get('pk')

        if not member_id:
            return Response({"status": status.HTTP_400_BAD_REQUEST, "message": "member_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not event_id:
            return Response({"status": status.HTTP_400_BAD_REQUEST, "message": "event_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            member = Member.objects.get(pk=member_id)
            print('member', member)
        except Member.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "member not found"},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            event = Event.objects.get(pk=event_id)
            print('event', event)
        except Event.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "event not found"},
                            status=status.HTTP_404_NOT_FOUND)

        participant = Participant.objects.filter(event=event, club_member__member=member)
        print('participant', participant)
        if not participant.exists():
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "참가자 명단에 없습니다."},
                            status=status.HTTP_404_NOT_FOUND)

        # Set group_type in context if needed
        context = super().get_serializer_context()
        context['group_type'] = participant.first().group_type

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
        print('EventViewSet')
        """
        GET 요청 시 해당 달 이벤트 목록(Events) 정보 반환
        요청 데이터: YYYY-MM-DD
        응답 데이터: Event (retrieve와 동일) 리스트
        """
        member_id = self.request.query_params.get('member_id')
        try:
            member = Member.objects.get(pk=member_id)
        except Event.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "member not found"},
                            status=status.HTTP_404_NOT_FOUND)

        queryset = EventUtils.get_month_events_queryset(request, member)
        serializer = EventDetailSerializer(queryset, many=True)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully event list',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)


class EventsUpcomingViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventDetailSerializer

    def list(self, request, *args, **kwargs):
        """
        GET 요청 시 다가 오는 이벤트 목록(Events) 정보 20개 반환
        응답 데이터: Event (retrieve와 동일) 리스트
        """
        member_id = self.request.query_params.get('member_id')
        #TODO: jwt에서 member_id 추출 가능하면, 토큰 방식으로 교체
        status_type = request.query_params.get('status_type')
        print('status_type', status_type)

        try:
            member = Member.objects.get(pk=member_id)
        except Event.DoesNotExist:
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "member not found"},
                            status=status.HTTP_404_NOT_FOUND)

        queryset = EventUtils.get_upcoming_events(status_type, member)
        serializer = EventDetailSerializer(queryset, many=True)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully upcoming events',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)
