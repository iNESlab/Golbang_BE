'''
MVP demo ver 0.0.2
2024.10.22

Cerly 작업 큐
'''
# clubs/tasks.py

from celery import shared_task
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from participants.models import Participant
from clubs.models import Club, ClubMember
from utils.push_fcm_notification import get_fcm_tokens_for_club_members, send_fcm_notifications

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

@shared_task
def send_club_creation_notification(club_id):
    """
    클럽(모임) 생성 시 FCM 알림을 전송하는 Celery 작업
    """
    try:
        club = Club.objects.get(id=club_id)
        fcm_tokens = get_fcm_tokens_for_club_members(club)
        logger.info(f"Retrieved fcm_tokens: {fcm_tokens}")

        # 모임 이름을 포함한 메시지 생성
        message_title = f"{club.name} 모임에 초대되었습니다."  # 메시지 제목
        message_body = f"모임이 성공적으로 생성되었습니다. {club.name} 모임에서 골프를 즐겨봅시다!"

        # FCM 메시지 전송
        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, club_id=club.id)
            logger.info(f"모임 생성 알림 전송 성공")
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")

    except ObjectDoesNotExist as e:
        logger.error(f"Error finding club {club_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending FCM notifications for club {club_id}: {e}")
