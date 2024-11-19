import pytest
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta

from clubs.models import Club
from events.models import Event
from events.tasks import send_event_notification_2_days_before, revoke_event_notifications


@pytest.mark.django_db
@patch('myapp.tasks.get_fcm_tokens_for_club_members')
@patch('myapp.tasks.send_fcm_notifications')
def test_send_event_notification_2_days_before(mock_send_fcm_notifications, mock_get_fcm_tokens_for_club_members):
    # Given: 이틀 후에 시작되는 이벤트와 FCM 토큰이 설정된 상황
    club = Club.objects.create(name="테스트 클럽")
    event = Event.objects.create(
        event_title="테스트 이벤트",
        club=club,
        start_date_time=timezone.now() + timedelta(days=2)
    )

    # FCM 토큰을 반환하도록 모의 설정
    mock_get_fcm_tokens_for_club_members.return_value = ['token1', 'token2']

    # When: 작업 실행
    send_event_notification_2_days_before()

    # Then: FCM 알림 전송 함수가 호출되었는지 확인
    mock_send_fcm_notifications.assert_called_once_with(
        ['token1', 'token2'],
        f"{club.name} 모임에서 진행하는 {event.event_title} 이벤트가 시작되기 이틀 전입니다.",
        "이벤트 상세 정보와 참석 여부를 확인해주세요."
    )

@pytest.mark.django_db
@patch('myapp.tasks.current_app.control.revoke')
@patch('myapp.tasks.cache.get')
@patch('myapp.tasks.cache.delete')
def test_revoke_event_notifications(mock_cache_delete, mock_cache_get, mock_revoke):
    # Given: 캐시에 저장된 작업 ID가 있는 이벤트 ID
    event_id = 1
    mock_cache_get.return_value = {
        'two_days_task_id': 'task_id_1',
        'one_hour_task_id': 'task_id_2',
        'end_task_id': 'task_id_3'
    }

    # When: 작업 취소 함수 실행
    revoke_event_notifications(event_id)

    # Then: 각 작업 ID에 대해 revoke가 호출되었는지 확인
    mock_revoke.assert_any_call('task_id_1', terminate=True)
    mock_revoke.assert_any_call('task_id_2', terminate=True)
    mock_revoke.assert_any_call('task_id_3', terminate=True)

    # 캐시에서 작업 ID가 삭제되었는지 확인
    mock_cache_delete.assert_called_once_with(f'event_{event_id}_task_ids')
