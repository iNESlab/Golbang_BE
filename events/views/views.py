'''
MVP demo ver 0.0.8
2024.08.02
events/views/views.py

역할: Django Rest Framework(DRF)를 사용하여 이벤트 API 엔드포인트의 로직을 처리
- 모임 관리자 : 멤버 핸디캡 자동 매칭 기능(팀전/개인전)
'''
from datetime import date, datetime
from django.db.models import Sum

from rest_framework.decorators import permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from clubs.models import ClubMember, Club
from clubs.views.club_common import IsClubAdmin, IsMemberOfClub
from participants.models import Participant
from events.models import Event
from events.serializers import EventCreateUpdateSerializer, EventDetailSerializer, EventResultSerializer, \
    ScoreCardSerializer
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

        if EventUtils.is_duplicated_participants(request.data.get('participants', [])):
            return handle_400_bad_request('Duplicate member_id found in participants.')

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
        event_id = self.kwargs.get('pk')

        try:
            event = Event.objects.get(pk=event_id)
            self.check_object_permissions(request, event.club)
        except Event.DoesNotExist:
            return handle_404_not_found('event', event_id)

        if EventUtils.is_duplicated_participants(request.data.get('participants',[])):
            return handle_400_bad_request('Duplicate member_id found in participants.')

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

    # 이벤트 개인전 결과 조회 (GET)
    @action(detail=True, methods=['get'], url_path='individual-results')
    def retrieve_individual_ranks(self, request, pk=None):
        """
        GET 요청 시 특정 이벤트(Event)의 결과, 즉 전체 순위를 반환한다.
        요청 데이터: 이벤트 ID
        응답 데이터: 참가자들의 순위 리스트 (sum_score 또는 handicap_score 기준 오름차순 정렬)
        """
        # user = request.user
        event_id = pk

        if not event_id:  # 이벤트 id가 없을 경우, 400 반환
            return handle_400_bad_request("event id is required")

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:  # 이벤트가 존재하지 않는 경우, 404 반환
            return handle_404_not_found('event', event_id)

        # 이벤트에 참여한 참가자들을 가져옴
        participants = Participant.objects.filter(event=event)

        # 시리얼라이저에 sort_type과 user를 컨텍스트로 넘김
        serializer = EventResultSerializer(
            event,
            context={
                'participants': participants,
                'request': request
            })

        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved ranks',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 이벤트 팀전 결과 조회 (GET)
    @action(detail=True, methods=['get'], url_path='team-results')
    def retrieve_team_results(self, request, pk=None):
        """
        GET 요청 시 특정 이벤트(Event)의 팀전 결과를 반환합니다.
        요청 데이터: 이벤트 ID
        응답 데이터: 조별 승리 팀 개수와 전체 점수에서 승리한 팀, 그리고 참가자 관련 데이터 포함
        """
        event_id = pk

        if not event_id:
            return handle_400_bad_request("event id is required")

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:
            return handle_404_not_found('event', event_id)

        # 조별 점수 및 승리 팀 계산
        event.calculate_group_scores()
        event.calculate_total_scores()

        # 추가적으로 participants 정보를 포함하기 위해 컨텍스트에 전달
        participants = Participant.objects.filter(event=event)

        # 시리얼라이저에 데이터를 넘겨서 JSON 응답으로 변환
        serializer = EventResultSerializer(
            event,
            context={
                'participants': participants,
                'request': request
            }
        )

        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved team results',
            'data': {
                'group_scores': {
                    'team_a_group_wins': event.team_a_group_wins,
                    'team_b_group_wins': event.team_b_group_wins,
                    'group_win_team': event.group_win_team,
                },
                'total_scores': {
                    'team_a_total_score': event.team_a_total_score,
                    'team_b_total_score': event.team_b_total_score,
                    'total_win_team': event.total_win_team,
                },
                'ranks': serializer.data  # 시리얼라이저를 통해 생성된 데이터 포함
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 이벤트 스코어 카드 조회
    @action(detail=True, methods=['get'], url_path='scores')
    def retrieve_scores(self, request, pk=None):
        user = request.user
        event_id = pk

        if not event_id:  # 이벤트 id가 없을 경우, 400 반환
            return handle_400_bad_request("event id is required")

        try:
            event = Event.objects.get(pk=event_id)
        except Event.DoesNotExist:  # 이벤트가 존재하지 않는 경우, 404 반환
            return handle_404_not_found('event', event_id)

        try:
            participant = Participant.objects.get(event=event, club_member__user=user)
        except Participant.DoesNotExist:
            return handle_404_not_found('participant', user)

        group_type = participant.group_type
        participants = Participant.objects.filter(event=event, group_type=group_type)

        # 팀 스코어를 저장할 변수들
        team_a_scores = None
        team_b_scores = None

        # 팀 타입이 NONE이 아닌 경우에만 팀 스코어 계산
        if any(p.team_type != Participant.TeamType.NONE for p in participants):
            team_a_scores = self.calculate_team_scores(participants, Participant.TeamType.TEAM1)
            team_b_scores = self.calculate_team_scores(participants, Participant.TeamType.TEAM2)

        # 개인전+팀전 스코어카드를 시리얼라이즈
        serializer = ScoreCardSerializer(participants, many=True)

        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved score cards',
            'data': {
                'participants': serializer.data,    # 개인전 스코어카드
                'team_a_scores': team_a_scores,     # 팀 A의 점수 (개인전인 경우 None)
                'team_b_scores': team_b_scores      # 팀 B의 점수 (개인전인 경우 None)
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 특정 팀의 전반, 후반, 전체, 핸디캡 적용 점수를 계산
    def calculate_team_scores(self, participants, team_type):
        team_participants = participants.filter(team_type=team_type) # 주어진 팀 타입(TEAM1 또는 TEAM2)에 속한 참가자들만 필터링
        front_nine_score = sum([p.get_front_nine_score() for p in team_participants])   # 팀에 속한 모든 참가자들의 전반전 점수를 합산
        back_nine_score = sum([p.get_back_nine_score() for p in team_participants])     # 팀에 속한 모든 참가자들의 후반전 점수를 합산
        total_score = sum([p.get_total_score() for p in team_participants])             # 전반전과 후반전 점수를 합산한 전체 점수를 계산
        handicap_score = sum([p.get_handicap_score() for p in team_participants])       # 각 참가자의 핸디캡 점수를 적용한 점수를 합산
        return {
            "front_nine_score": front_nine_score,
            "back_nine_score": back_nine_score,
            "total_score": total_score,
            "handicap_score": handicap_score
        }