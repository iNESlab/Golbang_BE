# events/tasks.py
'''
MVP demo ver 0.0.1
2024.10.22

Cerly 작업 큐
'''

from celery import shared_task, current_app
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache

from datetime import timezone, timedelta, datetime
import uuid

from events.models import Event
from utils.push_fcm_notification import get_fcm_tokens_for_club_members, send_fcm_notifications
from notifications.redis_interface import NotificationRedisInterface

from asgiref.sync import async_to_sync

import logging

logger = logging.getLogger(__name__)

# Redis 인터페이스 생성
redis_interface = NotificationRedisInterface()

@shared_task
def send_event_creation_notification(event_id):
    """
    이벤트 생성 시 FCM 알림을 전송하는 Celery 작업
    """
    try:
        event = Event.objects.get(id=event_id)
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)

        # 토큰 리스트 확인을 위한 로그 출력
        logger.info(f"Retrieved FCM tokens for event creation: {fcm_tokens}")

        message_title = f"[{club.name}] 모임에서 이벤트가 생성되었습니다."
        message_body = f"이벤트: {event.event_title}\n날짜: {event.start_date_time.strftime('%Y-%m-%d')}\n장소: {event.site}\n참석 여부를 체크해주세요."

        # Redis 저장용 알림 데이터 (status는 기본적으로 fail로 설정)
        #TODO: 반복되는 코드 함수화하는 것이 필요함.
        base_notification_data = {
            "title": message_title,
            "body": message_body,
            "status": "fail",
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, event_id=event.id)
            logger.info(f"이벤트 생성 알림 전송 성공: {event.event_title}")

            # 알림 전송 성공 후 Redis에 저장
            user_ids = club.members.values_list('id', flat=True)  # 모든 멤버 ID 가져오기
            print(f"user_ids: {user_ids}")
            for user_id in user_ids:
                print(f"user_id: {user_id}")
                # UUID 기반으로 notification_id 생성
                notification_id = str(uuid.uuid4())
                base_notification_data['notification_id'] = notification_id

                notification_data = {**base_notification_data, "status": "success"}
                print(f"notification준비 완료 {notification_id}, {notification_data}")

                async_to_sync(redis_interface.save_notification)(user_id, notification_id, notification_data, event_id=event.id)
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


        logger.info(f"Retrieved FCM tokens for event creation: {fcm_tokens}")


        message_title = f"[{club.name}] 모임에서 이벤트가 수정되었습니다."
        message_body = f"수정된 이벤트: {event.event_title}\n날짜: {event.start_date_time.strftime('%Y-%m-%d')}\n장소: {event.site}\n"

        # Redis 저장용 알림 데이터 (status는 기본적으로 fail로 설정)
        base_notification_data = {
            "title": message_title,
            "body": message_body,
            "status": "fail",
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, event_id=event.id)
            logger.info(f"이벤트 수정 알림 전송 성공: {event.event_title}")

            # 알림 전송 성공 후 Redis에 저장
            user_ids = club.members.values_list('id', flat=True)  # 모든 멤버 ID 가져오기
            print(f"user_ids: {user_ids}")
            for user_id in user_ids:
                print(f"user_id: {user_id}")
                # UUID 기반으로 notification_id 생성
                notification_id = str(uuid.uuid4())
                base_notification_data['notification_id'] = notification_id

                notification_data = {**base_notification_data, "status": "success"}
                print(f"notification준비 완료 {notification_id}, {notification_data}")

                async_to_sync(redis_interface.save_notification)(user_id, notification_id, notification_data, event_id=event.id)

        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")

    except ObjectDoesNotExist as e:
        logger.error(f"Error finding event {event_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending FCM notifications for event {event_id}: {e}")

@shared_task
def schedule_event_notifications_test(event_id):
    """
    테스트용: 이벤트 생성/수정 시 10초 전에 알림 예약하는 작업
    """
    try:
        event = Event.objects.get(id=event_id)
        now = timezone.now()

        # 10초 전 알림 예약
        ten_seconds_before = event.start_date_time - timedelta(seconds=10)
        if ten_seconds_before > now:
            countdown_until_10_seconds = (ten_seconds_before - now).total_seconds()
            ten_seconds_task = send_event_notification_10_seconds_before.apply_async(
                (event_id,), countdown=countdown_until_10_seconds
            )

        # task_id를 캐시에 저장
        cache.set(f'event_{event_id}_test_task_id', ten_seconds_task.id, timeout=None)

    except Event.DoesNotExist:
        logger.error(f"Event {event_id} does not exist")
    except Exception as e:
        logger.error(f"Error scheduling test notifications for event {event_id}: {e}")


@shared_task
def send_event_notification_10_seconds_before(event_id):
    """
    이벤트 시작 10초 전에 알림을 보내는 작업
    """
    try:
        event = Event.objects.get(id=event_id)
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)

        message_title = f"[{club.name}] 이벤트가 곧 시작됩니다!"
        message_body = f"이벤트: {event.event_title}\n10초 후에 시작됩니다. 참석 여부를 확인해주세요."

        # Redis 저장용 알림 데이터
        notification_data = {
            "title": message_title,
            "body": message_body,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, event_id=event.id)
            logger.info(f"10초 전 알림 전송 성공: {event.event_title}")

            # Redis 저장
            user_ids = club.members.values_list('id', flat=True)
            for user_id in user_ids:
                notification_id = str(uuid.uuid4())
                notification_data["notification_id"] = notification_id
                async_to_sync(redis_interface.save_notification)(user_id, notification_id, notification_data, event_id=event.id)

    except Event.DoesNotExist:
        logger.error(f"Event {event_id} does not exist")
    except Exception as e:
        logger.error(f"Error sending 10 seconds notification for event {event_id}: {e}")

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
            two_days_task = send_event_notification_2_days_before.apply_async((event_id,), countdown=countdown_until_2_days)

        # 1시간 전 알림 예약
        one_hour_before = event.start_date_time - timedelta(hours=1)
        if one_hour_before > now:
            countdown_until_1_hour = (one_hour_before - now).total_seconds()
            one_hour_task = send_event_notification_1_hour_before.apply_async((event_id,), countdown=countdown_until_1_hour)

        # 종료 후 알림 예약
        if event.end_date_time > now:
            countdown_until_end = (event.end_date_time - now).total_seconds()
            end_task = send_event_notification_event_ended.apply_async((event_id,), countdown=countdown_until_end)

        # task_ids를 캐시에 저장
        cache.set(f'event_{event_id}_task_ids', {
            'two_days_task_id': two_days_task.id,
            'one_hour_task_id': one_hour_task.id,
            'end_task_id': end_task.id
        }, timeout=None)

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
    # events = Event.objects.filter(start_date_time__date=now + timedelta(days=2))
    events = Event.objects.filter(start_date_time__date=now + timedelta(seconds=5))

    for event in events:
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)
        message_title = f"[{club.name}] 모임에서 진행하는 {event.event_title} 이벤트가 시작되기 이틀 전입니다."
        message_body = f"이벤트 상세 정보와 참석 여부를 확인해주세요."
        # Redis 저장용 알림 데이터 (status는 기본적으로 fail로 설정)
        base_notification_data = {
            "title": message_title,
            "body": message_body,
            "status": "fail",
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }
        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, event_id=event.id)
            logger.info(f"이틀 전 알림 전송 성공: {event.event_title}")

            # 알림 전송 성공 후 Redis에 저장
            user_ids = club.members.values_list('id', flat=True)  # 모든 멤버 ID 가져오기
            print(f"user_ids: {user_ids}")
            for user_id in user_ids:
                print(f"user_id: {user_id}")
                # UUID 기반으로 notification_id 생성
                notification_id = str(uuid.uuid4())
                base_notification_data['notification_id'] = notification_id

                notification_data = {**base_notification_data, "status": "success"}
                print(f"notification준비 완료 {notification_id}, {notification_data}")

                async_to_sync(redis_interface.save_notification)(user_id, notification_id, notification_data, event_id=event.id)

        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")


@shared_task
def send_event_notification_1_hour_before():
    """
    이벤트 시작 1시간 전에 알림을 보내는 작업
    """
    now = timezone.now()
    # events = Event.objects.filter(start_date_time__lte=now + timedelta(hours=1), start_date_time__gt=now)
    events = Event.objects.filter(start_date_time__lte=now + timedelta(seconds=2), start_date_time__gt=now)

    for event in events:
        club = event.club
        fcm_tokens = get_fcm_tokens_for_club_members(club)
        message_title = f"[{club.name}] 모임에서 진행하는 {event.event_title} 이벤트가 시작되기 1시간 전입니다."
        message_body = f"이벤트 상세 정보와 참석 여부를 확인해주세요."

        # Redis 저장용 알림 데이터 (status는 기본적으로 fail로 설정)
        base_notification_data = {
            "title": message_title,
            "body": message_body,
            "status": "fail",
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, event_id=event.id)
            logger.info(f"1시간 전 알림 전송 성공: {event.event_title}")

            # 알림 전송 성공 후 Redis에 저장
            user_ids = club.members.values_list('id', flat=True)  # 모든 멤버 ID 가져오기
            print(f"user_ids: {user_ids}")
            for user_id in user_ids:
                print(f"user_id: {user_id}")
                # UUID 기반으로 notification_id 생성
                notification_id = str(uuid.uuid4())
                base_notification_data['notification_id'] = notification_id

                notification_data = {**base_notification_data, "status": "success"}
                print(f"notification준비 완료 {notification_id}, {notification_data}")

                async_to_sync(redis_interface.save_notification)(user_id, notification_id, notification_data, event_id=event.id)

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
        message_title = f"[{club.name}] 모임에서 진행하는 {event.event_title} 이벤트가 종료되었습니다."
        message_body = f"이벤트 결과를 확인해주세요. (스코어 점수 수정은 이벤트 종료 2일 후까지만 가능합니다)"

        # Redis 저장용 알림 데이터 (status는 기본적으로 fail로 설정)
        base_notification_data = {
            "title": message_title,
            "body": message_body,
            "status": "fail",
            "timestamp": datetime.now().isoformat(),
            "read": False,
        }

        if fcm_tokens:
            send_fcm_notifications(fcm_tokens, message_title, message_body, event_id=event.id)
            logger.info(f"이벤트 종료 알림 전송 성공: {event.event_title}")

            # 알림 전송 성공 후 Redis에 저장
            user_ids = club.members.values_list('id', flat=True)  # 모든 멤버 ID 가져오기
            print(f"user_ids: {user_ids}")
            for user_id in user_ids:
                print(f"user_id: {user_id}")
                # UUID 기반으로 notification_id 생성
                notification_id = str(uuid.uuid4())
                base_notification_data['notification_id'] = notification_id

                notification_data = {**base_notification_data, "status": "success"}
                print(f"notification준비 완료 {notification_id}, {notification_data}")

                async_to_sync(redis_interface.save_notification)(user_id, notification_id, notification_data, event_id=event.id)
        else:
            logger.info(f"No FCM tokens found for club members in club: {club}")

def revoke_event_notifications(event_id):
    """
    기존 예약된 이벤트 알림 작업을 취소하는 함수
    """
    task_ids = cache.get(f'event_{event_id}_task_ids')

    if not task_ids:
        logger.info(f"No task IDs found for event {event_id}")
        return

    try:
        if task_ids.get('two_days_task_id'):
            current_app.control.revoke(task_ids['two_days_task_id'], terminate=True)
        if task_ids.get('one_hour_task_id'):
            current_app.control.revoke(task_ids['one_hour_task_id'], terminate=True)
        if task_ids.get('end_task_id'):
            current_app.control.revoke(task_ids['end_task_id'], terminate=True)

        # 작업 취소 후 캐시에서 제거
        cache.delete(f'event_{event_id}_task_ids')

    except Exception as e:
        logger.error(f"Error revoking event notification tasks for event {event_id}: {e}")