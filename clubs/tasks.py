'''
MVP demo ver 0.0.1
2024.08.28

Cerly 작업 큐
'''
from celery import shared_task
from django.db import transaction
from .models import ClubMember
import logging

logger = logging.getLogger(__name__)

# clubs/tasks.py

from celery import shared_task
from django.db import transaction
from participants.models import Participant
from clubs.models import Club, ClubMember
import logging

logger = logging.getLogger(__name__)

@shared_task
def calculate_club_ranks_and_points(club_id):
    """
    클럽 멤버들의 랭킹 및 포인트를 갱신하는 Celery 작업
    """
    try:
        with transaction.atomic():
            club = Club.objects.get(id=club_id)
            logger.info(f"Calculating ranks and points for club: {club}")

            # 클럽 멤버의 랭킹 계산
            ClubMember.calculate_avg_rank(club)
            ClubMember.calculate_handicap_avg_rank(club)
            logger.info(f"Ranks calculated for club: {club}")

            # 참가자 포인트 계산 및 업데이트 (조건에 맞는 참가자만 계산)
            participants = Participant.objects.filter(club_member__club=club, status_type__in=['ACCEPT', 'PARTY'])
            for participant in participants:
                # 포인트 계산 전에 조건을 확인
                if participant.rank == '0' or participant.handicap_rank == '0':
                    logger.info(f"Skipping points calculation for participant: {participant}")
                    continue
                participant.calculate_points()
                logger.info(f"Points calculated for participant: {participant}")

            # 클럽 멤버들의 총 포인트 업데이트
            for member in ClubMember.objects.filter(club=club):
                member.update_total_points()
            logger.info(f"Total points updated for members in club: {club}")

    except Exception as e:
        logger.error(f"Error updating ranks and points for club {club_id}: {e}")
