# utils/push_fcm_notification.py
import os

import firebase_admin
from firebase_admin import credentials, messaging
import logging

from clubs.models import ClubMember
from golbang.settings import BASE_DIR
from participants.models import Participant

logger = logging.getLogger(__name__)

cred_path = os.path.join(BASE_DIR, "serviceAccountKey.json")

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


def send_chat_message_notification(chat_room, sender_name, message_content, sender_id):
    '''
    채팅 메시지 FCM 알림 전송
    
    :param chat_room: 채팅방 객체
    :param sender_name: 발신자 이름
    :param message_content: 메시지 내용
    :param sender_id: 발신자 ID (자신에게는 알림 안 보내기 위해)
    '''
    try:
        # 채팅방 타입에 따라 FCM 토큰 가져오기
        if chat_room.chat_room_type == 'CLUB':
            # 모임 채팅방 - 모임 멤버들의 FCM 토큰 가져오기
            from clubs.models import Club
            club = Club.objects.get(id=chat_room.club_id)
            tokens = get_fcm_tokens_for_club_members(club)
        elif chat_room.chat_room_type == 'EVENT':
            # 이벤트 채팅방 - 이벤트 참여자들의 FCM 토큰 가져오기
            from events.models import Event
            event = Event.objects.get(id=chat_room.event_id)
            tokens = get_fcm_tokens_for_event_participants(event)
        else:
            logger.warning(f"지원하지 않는 채팅방 타입: {chat_room.chat_room_type}")
            return
        
        # 발신자 제외하고 알림 전송
        # FCM 토큰에서 발신자의 토큰을 제외하는 로직은 User 모델의 fcm_token과 sender_id를 비교해야 함
        # 일단 모든 토큰에 전송하고, 클라이언트에서 발신자 확인하여 표시하지 않도록 처리
        
        if not tokens:
            logger.warning("채팅방 멤버의 FCM 토큰이 없습니다.")
            return
        
        # 알림 제목과 내용 설정
        title = f"{chat_room.chat_room_name}"
        body = f"{sender_name}: {message_content[:50]}{'...' if len(message_content) > 50 else ''}"
        
        # data 필드에 채팅방 정보 포함
        additional_data = {
            "type": "chat_message",
            "chat_room_id": str(chat_room.id),
            "sender_id": str(sender_id),
            "sender_name": sender_name,
        }
        
        # 채팅방 타입에 따라 추가 데이터 설정
        if chat_room.chat_room_type == 'CLUB':
            additional_data["club_id"] = str(chat_room.club_id)
        elif chat_room.chat_room_type == 'EVENT':
            additional_data["event_id"] = str(chat_room.event_id)
        
        logger.info(f"채팅 메시지 알림 전송: {title} - {body}")
        logger.info(f"전송할 FCM 토큰 수: {len(tokens)}")
        
        # FCM 메시지 전송
        for token in tokens:
            message = messaging.Message(
                data=additional_data,
                notification=messaging.Notification(title=title, body=body),
                token=token,
            )
            
            try:
                response = messaging.send(message)
                logger.info(f'채팅 알림 전송 성공: {token[:10]}...')
            except Exception as e:
                logger.error(f'채팅 알림 전송 실패: 토큰={token[:10]}..., 오류={e}')
                
    except Exception as e:
        logger.error(f'채팅 메시지 알림 전송 중 오류: {e}')