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
from notifications.redis_interface import NotificationRedisInterface

import uuid
from datetime import datetime, time
from asgiref.sync import async_to_sync

import logging

logger = logging.getLogger(__name__)

# Redis 인터페이스 생성
redis_interface = NotificationRedisInterface()

@shared_task
def calculate_club_ranks_and_points(club_id=None):
    """
    모임 멤버들의 랭킹 및 포인트를 갱신하는 Celery 작업
    A. club_id=None 이면 모든 모임을 순회 (in settings.py - 매일 자정에 실행되는 코드)
    B. club_id 값이 있으면 해당 모임만 처리 (in club_statics.py)
    """
    # 대상 클럽 리스트 얻기
    if club_id:
        clubs = Club.objects.filter(id=club_id)
    else:
        clubs = Club.objects.all()

    # 모임 순회
    for club in clubs:
        try:
            with transaction.atomic():
                logger.info(f"Calculating ranks and points for club: {club}")

                # 클럽 멤버의 랭킹 계산
                ClubMember.calculate_avg_rank(club)
                ClubMember.calculate_handicap_avg_rank(club)
                logger.info(f"Ranks calculated for club: {club}")

                # 참가자 포인트 계산
                participants = Participant.objects.filter(
                    club_member__club=club,
                    status_type__in=['ACCEPT', 'PARTY']
                )
                for p in participants:
                    if p.rank == '0' or p.handicap_rank == '0':
                        logger.info(f"Skipping points for participant: {p}")
                        continue
                    p.calculate_points()
                    logger.info(f"Points calculated for participant: {p}")

                # 클럽 멤버들의 총 포인트 업데이트
                for member in ClubMember.objects.filter(club=club):
                    member.update_total_points()
                logger.info(f"Total points updated for members in club: {club}")

        except Exception as e:
            logger.error(f"Error updating ranks/points for club {club.id}: {e}")

@shared_task
def send_club_creation_notification(club_id):
    """
    클럽(모임) 생성 시 FCM 알림을 전송하고 Redis에 저장하는 Celery 작업
    """
    try:
        club = Club.objects.get(id=club_id)
        
        # 🔧 수정: 생성자(관리자) 제외하고 FCM 토큰 가져오기
        from clubs.models import ClubMember
        admin_members = ClubMember.objects.filter(club=club, role='admin').values_list('user_id', flat=True)
        logger.info(f"모임 생성자(관리자) ID들: {list(admin_members)}")
        
        fcm_tokens = get_fcm_tokens_for_club_members(club, exclude_user_ids=list(admin_members))
        logger.info(f"Retrieved fcm_tokens: {fcm_tokens}")

        # 모임 이름을 포함한 메시지 생성
        message_title = f"{club.name} 모임에 초대되었습니다."
        message_body = f"{club.name} 달력을 눌러 새로운 일정을 만들어보세요!"

        # Redis 저장용 알림 데이터 (status는 기본적으로 fail로 설정)
        # TODO: 반복되는 코드 함수화하는 것이 필요함.
        base_notification_data = {
            "title": message_title,
            "body": message_body,
            "status": "fail",
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }

        # FCM 메시지 전송
        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, club_id=club.id)
            logger.info(f"모임 생성 알림 전송 성공")

            # 🔧 수정: 생성자(관리자) 제외하고 Redis에 저장
            user_ids = club.members.exclude(id__in=admin_members).values_list('id', flat=True)  # 생성자 제외한 멤버 ID만
            print(f"user_ids: {user_ids}")
            for user_id in user_ids:
                print(f"user_id: {user_id}")
                # UUID 기반으로 notification_id 생성
                notification_id = str(uuid.uuid4())
                base_notification_data['notification_id'] = notification_id

                notification_data = {**base_notification_data, "status": "success"}
                print(f"notification준비 완료 {notification_id}, {notification_data}")

                async_to_sync(redis_interface.save_notification)(user_id, notification_id, notification_data, club_id=club.id)
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")

    except ObjectDoesNotExist as e:
        logger.error(f"Error finding club {club_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending FCM notifications for club {club_id}: {e}")
