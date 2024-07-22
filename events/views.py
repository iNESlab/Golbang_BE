# events/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from clubMembers.models import ClubMember
from .models import Event
from .serializers import EventCreateSerializer, EventDetailSerializer


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
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

    def retrieve(self, request, *args, **kwargs):
        """
        GET 요청 시 특정 이벤트(Event) 정보 반환
        요청 데이터: Event ID
        응답 데이터: Event 정보 (Event ID, 생성자 ID, 참가자 리스트, 제목, 장소, 시작/종료 시간, 반복 타입, 게임 모드, 알람 시간)
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)