# events/tasks.py
'''
MVP demo ver 0.0.1
2024.10.22

Cerly 작업 큐
'''

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from events.models import Event
from utils.push_fcm_notification import get_fcm_tokens_for_club_members, send_fcm_notifications

import logging

logger = logging.getLogger(__name__)

@shared_task
def send_event_creation_notification(event_id):
    """
    이벤트 생성 시 FCM 알림을 전송하는 Celery 작업
    """
    try:
        event = Event.objects.get(id=event_id)
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)

        message_title = f"{club.name} 모임에서 이벤트가 생성되었습니다."
        message_body = f"{event.event_title} 이벤트의 날짜는 {event.start_date_time.strftime('%Y-%m-%d')}이며, 장소는 {event.site}입니다. 참석 여부를 체크해주세요."

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body)
            logger.info(f"이벤트 생성 알림 전송 성공: {event.event_title}")
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")

    except ObjectDoesNotExist as e:
        logger.error(f"Error finding event {event_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending FCM notifications for event {event_id}: {e}")
