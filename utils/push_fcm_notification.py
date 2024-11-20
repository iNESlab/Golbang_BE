# utils/push_fcm_notification.py
import os

import firebase_admin
from firebase_admin import credentials, messaging
import logging

from clubs.models import ClubMember
from golbang.settings import BASE_DIR
from participants.models import Participant

logger = logging.getLogger(__name__)

cred_path = os.path.join(BASE_DIR, "golbang-test-31a73-firebase-adminsdk-wqtgg-f611444c79.json")

# Firebase 앱 초기화
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.error(f'Firebase 초기화 중 오류 발생: {e}')

def get_fcm_tokens_for_club_members(club):
    '''
    주어진 클럽의 모든 멤버의 FCM 토큰을 가져오는 함수

    :param club: 클럽(모임) 객체
    :return: 클럽(모임) 멤버들의 FCM 토큰 리스트
    '''
    tokens = ClubMember.objects.filter(club=club).values_list('user__fcm_token', flat=True)
    return [token for token in tokens if token]


def get_fcm_tokens_for_event_participants(event):
    '''
    주어진 이벤트의 모든 참가자의 FCM 토큰을 가져오는 함수

    :param event: 이벤트 객체
    :return: 이벤트 참가자들의 FCM 토큰 리스트
    '''
    return list(Participant.objects.filter(event=event).values_list('club_member__user__fcm_token', flat=True))


def send_fcm_notifications(tokens, title, body, event_id=None, club_id=None):
    '''
    주어진 FCM 토큰 리스트에 일괄적으로 푸시 알림을 전송하는 함수

    :param tokens: FCM 토큰 리스트
    :param title: 알림의 제목
    :param body: 알림의 내용
    '''
    if not tokens:
        logger.warning("FCM 토큰이 없습니다. 알림을 전송하지 않습니다.")
        return

        # 조건에 따라 data 필드 구성
    additional_data = {}
    if event_id:
        additional_data["event_id"] = str(event_id)  # 이벤트 ID만 포함
    elif club_id:
        additional_data["club_id"] = str(club_id)  # 모임 ID만 포함

    logger.info(f"send_fcm_notifications 전송할 FCM 토큰: {tokens}")  # 토큰 리스트 출력
    logger.info(f"이벤트/모임 데이터: {additional_data}")

    for token in tokens:
        print(f"token: {token}, type: {type(tokens)}")

    for token in tokens:
        # 개별 메시지 객체 생성
        message = messaging.Message(
            data=additional_data,# 이벤트/모임 id 필ㅂ1
            notification=messaging.Notification(title=title, body=body),
            token=token,
        )

        try:
            # 메시지 전송
            response = messaging.send(message)
            logger.info(f'{token}에 메시지가 성공적으로 전송되었습니다.')
        except Exception as e:
            logger.error(f'FCM 메시지 전송 실패: 토큰={token}, 오류={e}')
            print(f'FCM 메시지 전송 중 오류 발생: {e}')