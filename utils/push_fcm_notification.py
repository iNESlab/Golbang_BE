# utils/push_fcm_notification.py

import firebase_admin
from firebase_admin import messaging
import logging

from clubs.models import ClubMember
from participants.models import Participant

logger = logging.getLogger(__name__)

def get_fcm_tokens_for_club_members(club):
    '''
    주어진 클럽의 모든 멤버의 FCM 토큰을 가져오는 함수

    :param club: 클럽(모임) 객체
    :return: 클럽(모임) 멤버들의 FCM 토큰 리스트
    '''
    return list(ClubMember.objects.filter(club=club).values_list('user__fcm_token', flat=True))

def get_fcm_tokens_for_event_participants(event):
    '''
    주어진 이벤트의 모든 참가자의 FCM 토큰을 가져오는 함수

    :param event: 이벤트 객체
    :return: 이벤트 참가자들의 FCM 토큰 리스트
    '''
    return list(Participant.objects.filter(event=event).values_list('club_member__user__fcm_token', flat=True))


def send_fcm_notifications(tokens, title, body):
    '''
    주어진 FCM 토큰 리스트에 일괄적으로 푸시 알림을 전송하는 함수

    :param tokens: FCM 토큰 리스트
    :param title: 알림의 제목
    :param body: 알림의 내용
    '''
    if not tokens:
        logger.warning("FCM 토큰이 없습니다. 알림을 전송하지 않습니다.")
        return

    # 메시지 목록 생성
    messages = [
        messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
        )
        for token in tokens
    ]

    try:
        # 일괄 메시지 전송
        response = messaging.send_all(messages)
        logger.info(f'{response.success_count}개의 메시지가 성공적으로 전송되었습니다.')
        if response.failure_count > 0:
            logger.warning(f'{response.failure_count}개의 메시지 전송에 실패했습니다.')
    except Exception as e:
        logger.error(f'FCM 메시지 전송 중 오류 발생: {e}')
