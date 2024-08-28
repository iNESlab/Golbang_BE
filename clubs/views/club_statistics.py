'''
MVP demo ver 0.0.9
2024.08.27
clubs/views/club_statistics.py

역할: 모임 내 랭킹 조회
'''
import logging

from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from participants.models import Participant
from participants.serializers import EventStatisticsSerializer

from . import ClubViewSet
from ..models import Club, ClubMember
from utils.error_handlers import handle_404_not_found, handle_400_bad_request
from ..serializers import ClubRankingSerializer, ClubStatisticsSerializer
from clubs.tasks import calculate_club_ranks_and_points

logger = logging.getLogger(__name__)

class ClubStatisticsViewSet(ClubViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='ranks')
    def retrieve_statistics(self, request):
        """
        특정 클럽의 통계 및 이벤트 정보를 조회하는 엔드포인트
        """
        logger.info("retrieve_statistics called")
        club_id = request.query_params.get('club_id')

        if not club_id:
            logger.error("Club ID is missing in the request.")
            return handle_400_bad_request("club_id is required.")

        try:
            club = Club.objects.get(id=club_id)
            logger.info(f"Club found: {club}")
        except Club.DoesNotExist:
            logger.error(f"Club not found with id: {club_id}")
            return handle_404_not_found('club', club_id)

        # 사용자와 클럽 멤버 확인
        user = request.user
        logger.info(f"Request made by user: {user}")
        try:
            # 클럽 멤버가 있는지 확인
            club_member = ClubMember.objects.get(club=club, user=user)
            logger.info(f"Club member found: {club_member}")
        except ClubMember.DoesNotExist:
            logger.error(f"Club member not found for user {user} in club {club}")
            return handle_404_not_found('club member', club_id)

        # 비동기 작업으로 랭킹 및 포인트 계산 수행
        calculate_club_ranks_and_points.delay(club_id)
        logger.info(f"Celery task scheduled for updating ranks and points for club: {club_id}")

        # 클럽 멤버의 랭킹 정보 시리얼라이징
        ranking_serializer = ClubRankingSerializer(club_member)
        logger.info(f"Ranking data serialized: {ranking_serializer.data}")

        # 클럽에 있는 이벤트에 대한 참가자 정보 시리얼라이징
        participants = Participant.objects.filter(club_member=club_member)
        event_serializer = EventStatisticsSerializer(participants, many=True)
        logger.info(f"Event data serialized for {len(participants)} participants")

        # 전체 응답 시리얼라이징
        data = {
            'ranking': ranking_serializer.data,
            'events': event_serializer.data
        }
        return Response({
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved statistics in club',
            'data': data
        }, status=status.HTTP_200_OK)