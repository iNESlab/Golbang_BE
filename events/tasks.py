# events/tasks.py
'''
MVP demo ver 0.0.1
2024.10.22

Cerly 작업 큐
'''

from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist

from datetime import timezone, timedelta

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


@shared_task
def send_event_update_notification(event_id):
    """
    이벤트 수정 시 FCM 알림을 전송하는 Celery 작업
    """
    try:
        event = Event.objects.get(id=event_id)
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)

        message_title = f"{club.name} 모임에서 이벤트가 수정되었습니다."
        message_body = f"수정된 {event.event_title} 이벤트의 날짜는 {event.start_date_time.strftime('%Y-%m-%d')}이며, 장소는 {event.site}입니다. 다시 참석 여부를 체크해주세요."

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body)
            logger.info(f"이벤트 수정 알림 전송 성공: {event.event_title}")
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")

    except ObjectDoesNotExist as e:
        logger.error(f"Error finding event {event_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending FCM notifications for event {event_id}: {e}")

@shared_task
def schedule_event_notifications(event_id):
    """
    이벤트 생성/수정 시 이틀 전, 1시간 전, 종료 후 알림 예약하는 작업
    """
    try:
        event = Event.objects.get(id=event_id)
        now = timezone.now()

        # 이틀 전 알림 예약
        two_days_before = event.start_date_time - timedelta(days=2)
        if two_days_before > now:
            countdown_until_2_days = (two_days_before - now).total_seconds()
            send_event_notification_2_days_before.apply_async((event_id,), countdown=countdown_until_2_days)

        # 1시간 전 알림 예약
        one_hour_before = event.start_date_time - timedelta(hours=1)
        if one_hour_before > now:
            countdown_until_1_hour = (one_hour_before - now).total_seconds()
            send_event_notification_1_hour_before.apply_async((event_id,), countdown=countdown_until_1_hour)

        # 종료 후 알림 예약
        if event.end_date_time > now:
            countdown_until_end = (event.end_date_time - now).total_seconds()
            send_event_notification_event_ended.apply_async((event_id,), countdown=countdown_until_end)

    except Event.DoesNotExist:
        logger.error(f"Event {event_id} does not exist")
    except Exception as e:
        logger.error(f"Error scheduling event notifications for event {event_id}: {e}")

@shared_task
def send_event_notification_2_days_before():
    """
    이벤트 시작 이틀 전에 알림을 보내는 작업
    """
    now = timezone.now()
    events = Event.objects.filter(start_date_time__date=now + timedelta(days=2))

    for event in events:
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)
        message_title = f"{club.name} 모임에서 진행하는 {event.event_title} 이벤트가 시작되기 이틀 전입니다."
        message_body = f"이벤트 상세 정보와 참석 여부를 확인해주세요."

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body)
            logger.info(f"이틀 전 알림 전송 성공: {event.event_title}")
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")


@shared_task
def send_event_notification_1_hour_before():
    """
    이벤트 시작 1시간 전에 알림을 보내는 작업
    """
    now = timezone.now()
    events = Event.objects.filter(start_date_time__lte=now + timedelta(hours=1), start_date_time__gt=now)

    for event in events:
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)
        message_title = f"{club.name} 모임에서 진행하는 {event.event_title} 이벤트가 시작되기 1시간 전입니다."
        message_body = f"이벤트 상세 정보와 참석 여부를 확인해주세요."

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body)
            logger.info(f"1시간 전 알림 전송 성공: {event.event_title}")
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")


@shared_task
def send_event_notification_event_ended():
    """
    이벤트 종료 후 알림을 보내는 작업
    """
    now = timezone.now()
    events = Event.objects.filter(end_date_time__lte=now, end_date_time__gt=now - timedelta(hours=1))

    for event in events:
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)
        message_title = f"{club.name} 모임에서 진행하는 {event.event_title} 이벤트가 종료되었습니다."
        message_body = f"이벤트 결과를 확인해주세요. (스코어 점수 수정은 이벤트 종료 2일 후까지만 가능합니다)"

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body)
            logger.info(f"이벤트 종료 알림 전송 성공: {event.event_title}")
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")