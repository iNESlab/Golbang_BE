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


def send_club_invitation_notification(club, invited_user, inviter_name):
    """
    클럽 초대 FCM 알림 전송
    
    :param club: 클럽 객체
    :param invited_user: 초대받은 사용자 객체
    :param inviter_name: 초대한 사용자 이름
    """
    try:
        if not invited_user.fcm_token:
            logger.warning(f"사용자 {invited_user.name}의 FCM 토큰이 없습니다.")
            return
            
        message_title = f"{club.name} 모임에 초대되었습니다"
        message_body = f"{inviter_name}님이 {club.name} 모임에 초대했습니다"
        
        additional_data = {
            "club_id": str(club.id),
            "notification_type": "club_invitation"
        }
        
        message = messaging.Message(
            data=additional_data,
            notification=messaging.Notification(title=message_title, body=message_body),
            token=invited_user.fcm_token,
        )
        
        response = messaging.send(message)
        logger.info(f'클럽 초대 알림이 {invited_user.name}에게 성공적으로 전송되었습니다.')
        
    except Exception as e:
        logger.error(f'클럽 초대 알림 전송 중 오류 발생: {e}')

def send_club_application_notification(club, applicant_user):
    """
    클럽 가입 신청 FCM 알림 전송 (관리자들에게)
    
    :param club: 클럽 객체
    :param applicant_user: 신청한 사용자 객체
    """
    try:
        # 클럽 관리자들의 FCM 토큰 가져오기
        admin_tokens = ClubMember.objects.filter(
            club=club, 
            role='admin'
        ).values_list('user__fcm_token', flat=True)
        
        admin_tokens = [token for token in admin_tokens if token]
        
        if not admin_tokens:
            logger.warning(f"클럽 {club.name}의 관리자 FCM 토큰이 없습니다.")
            return
            
        message_title = f"{club.name} 모임에 가입 신청이 있습니다"
        message_body = f"{applicant_user.name}님이 {club.name} 모임 가입을 신청했습니다"
        
        additional_data = {
            "club_id": str(club.id),
            "notification_type": "club_application"
        }
        
        for token in admin_tokens:
            message = messaging.Message(
                data=additional_data,
                notification=messaging.Notification(title=message_title, body=message_body),
                token=token,
            )
            
            response = messaging.send(message)
            logger.info(f'클럽 가입 신청 알림이 관리자에게 성공적으로 전송되었습니다.')
        
    except Exception as e:
        logger.error(f'클럽 가입 신청 알림 전송 중 오류 발생: {e}')

def send_club_application_result_notification(club, applicant_user, is_approved):
    """
    클럽 가입 신청 결과 FCM 알림 전송
    
    :param club: 클럽 객체
    :param applicant_user: 신청한 사용자 객체
    :param is_approved: 승인 여부 (True: 승인, False: 거절)
    """
    try:
        if not applicant_user.fcm_token:
            logger.warning(f"사용자 {applicant_user.name}의 FCM 토큰이 없습니다.")
            return
            
        if is_approved:
            message_title = f"{club.name} 모임 가입이 승인되었습니다"
            message_body = f"축하합니다! {club.name} 모임에 가입되었습니다"
        else:
            message_title = f"{club.name} 모임 가입이 거절되었습니다"
            message_body = f"죄송합니다. {club.name} 모임 가입이 거절되었습니다"
        
        additional_data = {
            "club_id": str(club.id),
            "notification_type": "club_application_result",
            "is_approved": str(is_approved)
        }
        
        message = messaging.Message(
            data=additional_data,
            notification=messaging.Notification(title=message_title, body=message_body),
            token=applicant_user.fcm_token,
        )
        
        response = messaging.send(message)
        logger.info(f'클럽 가입 신청 결과 알림이 {applicant_user.name}에게 성공적으로 전송되었습니다.')
        
    except Exception as e:
        logger.error(f'클럽 가입 신청 결과 알림 전송 중 오류 발생: {e}')

def send_chat_message_notification(chat_room, sender_name, message_content, sender_id):
    '''
    채팅 메시지 FCM 알림 전송 (사용자 알림 설정 확인)
    
    :param chat_room: 채팅방 객체
    :param sender_name: 발신자 이름
    :param message_content: 메시지 내용
    :param sender_id: 발신자 ID (자신에게는 알림 안 보내기 위해)
    '''
    try:
        # 🔧 추가: 알림 설정 확인을 위한 import
        from chat.models import ChatNotificationSettings
        # 채팅방 타입에 따라 FCM 토큰 가져오기
        if chat_room.chat_room_type == 'CLUB':
            # 모임 채팅방 - 모든 클럽 멤버에게 알림 전송
            from clubs.models import Club
            from chat.models import ChatRoomParticipant
            club = Club.objects.get(id=chat_room.club_id)
            
            # 채팅방에 참여한 사용자들 조회 (참고용)
            participants = ChatRoomParticipant.objects.filter(
                chat_room=chat_room,
                is_active=True
            ).values_list('user_id', flat=True)
            
            logger.info(f"🔍 채팅방 참여자 ID 목록: {list(participants)}")
            
            # 🔧 수정: 모든 클럽 멤버의 FCM 토큰 가져오기
            all_tokens = get_fcm_tokens_for_club_members(club)
            
            # 🔧 디버그: 전체 클럽 멤버 정보 출력
            logger.info(f"🔍 === 클럽 '{club.name}' 전체 멤버 정보 ===")
            from clubs.models import ClubMember
            club_members = ClubMember.objects.filter(club=club).select_related('user')
            for i, member in enumerate(club_members):
                logger.info(f"🔍 멤버 {i+1}: ID={member.user.id}, 이름={member.user.name}, FCM토큰={member.user.fcm_token[:20] if member.user.fcm_token else 'None'}...")
            
            logger.info(f"🔍 전체 FCM 토큰 수: {len(all_tokens)}")
            for i, token in enumerate(all_tokens):
                logger.info(f"🔍 토큰 {i+1}: {token[:20]}...")
            
            tokens = []
            processed_tokens = set()  # 중복 토큰 방지
            
            for token_data in all_tokens:
                if token_data in processed_tokens:
                    continue  # 이미 처리된 토큰은 스킵
                    
                # User 모델에서 FCM 토큰과 사용자 ID 매칭
                from accounts.models import User
                try:
                    # get() 대신 filter() 사용하여 중복 처리
                    users = User.objects.filter(fcm_token=token_data)
                    if users.exists():
                        user = users.first()  # 첫 번째 사용자만 선택
                        # 🔧 수정: 클럽 채팅방에서는 모든 클럽 멤버에게 알림 전송
                        # 🔧 주석처리: 알림 설정 확인 (테스트용)
                        # try:
                        #     notification_setting = ChatNotificationSettings.objects.get(
                        #         user=user,
                        #         chat_room=chat_room
                        #     )
                        #     if not notification_setting.is_enabled:
                        #         logger.info(f"🔕 사용자 {user.name}의 알림이 비활성화됨")
                        #         continue
                        # except ChatNotificationSettings.DoesNotExist:
                        #     # 설정이 없으면 기본값(True)으로 처리
                        #     logger.info(f"🔔 사용자 {user.name}의 알림 설정 없음, 기본값(활성화) 적용")
                        
                        tokens.append(token_data)
                        processed_tokens.add(token_data)
                except Exception as e:
                    logger.warning(f"사용자 조회 실패 (토큰: {token_data[:10]}...): {e}")
                    continue
            
            logger.info(f"클럽 '{club.name}' 참여자 수: {len(participants)}명, FCM 전송 대상: {len(tokens)}명")
            
        elif chat_room.chat_room_type == 'EVENT':
            # 이벤트 채팅방 - 채팅방에 참여하지 않은 참가자들에게만 알림 전송
            from events.models import Event
            from chat.models import ChatRoomParticipant
            event = Event.objects.get(id=chat_room.event_id)
            
            # 채팅방에 참여한 사용자들 조회
            participants = ChatRoomParticipant.objects.filter(
                chat_room=chat_room,
                is_active=True
            ).values_list('user_id', flat=True)
            
            # 참여하지 않은 참가자들의 FCM 토큰만 가져오기
            all_tokens = get_fcm_tokens_for_event_participants(event)
            tokens = []
            processed_tokens = set()  # 중복 토큰 방지
            
            for token_data in all_tokens:
                if token_data in processed_tokens:
                    continue  # 이미 처리된 토큰은 스킵
                    
                # User 모델에서 FCM 토큰과 사용자 ID 매칭
                from accounts.models import User
                try:
                    # get() 대신 filter() 사용하여 중복 처리
                    users = User.objects.filter(fcm_token=token_data)
                    if users.exists():
                        user = users.first()  # 첫 번째 사용자만 선택
                        if user.id not in participants:  # 참여하지 않은 사용자만
                            # 🔧 주석처리: 알림 설정 확인 (테스트용)
                            # try:
                            #     notification_setting = ChatNotificationSettings.objects.get(
                            #         user=user,
                            #         chat_room=chat_room
                            #     )
                            #     if not notification_setting.is_enabled:
                            #         logger.info(f"🔕 사용자 {user.name}의 알림이 비활성화됨")
                            #         continue
                            # except ChatNotificationSettings.DoesNotExist:
                            #     # 설정이 없으면 기본값(True)으로 처리
                            #     logger.info(f"🔔 사용자 {user.name}의 알림 설정 없음, 기본값(활성화) 적용")
                            
                            tokens.append(token_data)
                            processed_tokens.add(token_data)
                except Exception as e:
                    logger.warning(f"사용자 조회 실패 (토큰: {token_data[:10]}...): {e}")
                    continue
            
            logger.info(f"이벤트 '{event.title}' 참여자 수: {len(participants)}명, FCM 전송 대상: {len(tokens)}명")
        else:
            logger.warning(f"지원하지 않는 채팅방 타입: {chat_room.chat_room_type}")
            return
        
        # 발신자 제외하고 알림 전송
        # 발신자의 FCM 토큰을 제외하여 자신에게는 알림이 가지 않도록 처리
        sender_fcm_token = None
        try:
            from accounts.models import User
            sender = User.objects.get(id=sender_id)
            sender_fcm_token = sender.fcm_token
        except User.DoesNotExist:
            logger.warning(f"발신자 사용자를 찾을 수 없습니다: {sender_id}")
        
        # 🔧 디버그: 토큰 수 확인
        logger.info(f"🔍 발신자 제외 전 토큰 수: {len(tokens)}")
        logger.info(f"🔍 발신자 FCM 토큰: {sender_fcm_token[:10] if sender_fcm_token else 'None'}...")
        
        # 🔧 디버그: 모든 사용자 FCM 토큰 출력
        logger.info("🔍 === 모든 사용자 FCM 토큰 ===")
        for i, token in enumerate(tokens):
            logger.info(f"🔍 사용자 {i+1}: {token[:20]}...")
        
        # 🔧 디버그: 발신자 정보 상세 출력
        try:
            from accounts.models import User
            sender = User.objects.get(id=sender_id)
            logger.info(f"🔍 발신자 정보: ID={sender.id}, 이름={sender.name}, FCM토큰={sender.fcm_token[:20] if sender.fcm_token else 'None'}...")
        except Exception as e:
            logger.error(f"🔍 발신자 정보 조회 실패: {e}")
        
        # 발신자 토큰 제외
        if sender_fcm_token and sender_fcm_token in tokens:
            tokens = [token for token in tokens if token != sender_fcm_token]
            logger.info(f"발신자 토큰 제외: {sender_fcm_token[:10]}...")
            logger.info(f"🔍 발신자 제외 후 토큰 수: {len(tokens)}")
        else:
            logger.info(f"🔍 발신자 토큰이 토큰 리스트에 없음 또는 None")
        
        if not tokens:
            logger.warning("채팅방 멤버의 FCM 토큰이 없습니다.")
            logger.warning(f"🔍 원본 토큰 수: {len(tokens)}")
            return
        
        # 알림 제목과 내용 설정
        title = f"{chat_room.chat_room_name}"
        
        # 이미지 메시지인지 확인
        import json
        try:
            message_data = json.loads(message_content)
            if message_data.get('type') == 'image':
                body = f"{sender_name}: 사진을 보냈습니다"
            else:
                body = f"{sender_name}: {message_content[:50]}{'...' if len(message_content) > 50 else ''}"
        except (json.JSONDecodeError, TypeError):
            # JSON이 아닌 경우 일반 텍스트로 처리
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
            additional_data["chat_room_id"] = str(chat_room.club_id)  # 🔧 추가: 채팅방 ID
            additional_data["chat_room_type"] = "CLUB"  # 🔧 추가: 채팅방 타입
        elif chat_room.chat_room_type == 'EVENT':
            additional_data["event_id"] = str(chat_room.event_id)
            additional_data["chat_room_id"] = str(chat_room.event_id)  # 🔧 추가: 채팅방 ID
            additional_data["chat_room_type"] = "EVENT"  # 🔧 추가: 채팅방 타입
        
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