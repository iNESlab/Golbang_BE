'''
MVP demo ver 0.0.9
2024.08.27
clubs/views/club_statistics.py

역할: 모임 내 랭킹 조회
'''

from participants.models import Participant
from events.models import Event

from . import ClubViewSet
from ..models import Club, ClubMember
from utils.error_handlers import handle_404_not_found, handle_400_bad_request

from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg

from ..utils import calculate_event_points


class ClubStatisticsViewSet(ClubViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='club-info')
    def club_info(self, request):
        '''
        모임별 랭킹 및 이벤트 리스트 조회
        GET /clubs/statistics/club-info/?club_id={club_id}
        '''
        club_id = request.query_params.get('club_id')
        if not club_id:
            return handle_400_bad_request('club_id is required.')

        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return handle_404_not_found('Club', club_id)

        user = request.user
        try:
            club_member = ClubMember.objects.get(club=club, user=user)
        except ClubMember.DoesNotExist:
            return handle_404_not_found('Club member', f"for club_id {club_id} and user {user.id}")

        # 모임별 랭킹 데이터 생성
        total_events = Event.objects.filter(club=club).count()
        participation_count = Participant.objects.filter(club_member=club_member).count()
        participation_rate = (participation_count / total_events) * 100 if total_events > 0 else 0
        total_points = Participant.objects.filter(club_member=club_member).aggregate(total_points=Sum('sum_score'))['total_points'] or 0

        # 사용자 순위 계산
        participants_with_rank = Participant.objects.filter(club_member__club=club).annotate(total_points=Sum('sum_score')).order_by('-total_points')

        rank = None
        for idx, participant in enumerate(participants_with_rank, start=1):
            if participant.club_member.user == user:
                rank = idx
                break

        # 이벤트 리스트 생성
        events = Event.objects.filter(club=club).values('id', 'event_title', 'start_date_time')
        event_list = []
        for event in events:
            participant = Participant.objects.filter(event_id=event['id'], club_member=club_member).first()
            if participant:
                event_participants = Participant.objects.filter(event_id=event['id'], club_member__club=club).annotate(total_points=Sum('sum_score')).order_by('-total_points')
                event_rank = None
                for idx, p in enumerate(event_participants, start=1):
                    if p.club_member.user == user:
                        event_rank = idx
                        break

                event_list.append({
                    "event_id": event['id'],
                    "event_name": event['event_title'],
                    "total_score": participant.sum_score,
                    "points": participant.sum_score,  # 포인트 계산 방식에 따라 수정 가능
                    "total_participants": event_participants.count(),
                    "rank": event_rank
                })

        # 응답 데이터 생성
        data = {
            "ranking": {
                "club_id": club.id,
                "rank": rank,
                "total_events": total_events,
                "participation_count": participation_count,
                "participation_rate": round(participation_rate, 1),
                "total_points": total_points
            },
            "events": event_list
        }

        return Response({
            "status": status.HTTP_200_OK,
            "message": "Successfully retrieved club information",
            "data": data
        }, status=status.HTTP_200_OK)
