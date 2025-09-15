import json
import logging
import asyncio
import base64
import os
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from django.conf import settings
from .models import ChatRoom, ChatMessage, ChatRoomParticipant, ChatConnection, MessageReadStatus, ChatNotification, ChatReaction

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    """
    STOMP WebSocket 채팅 Consumer
    연결 관리, 메시지 전송/수신, 참가자 관리 담당
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_name = None
        self.room_group_name = None
        self.user = None
        self.connection_id = None
        self.chat_room = None
        
        # 연결 상태 추적
        self.is_connected = False
        self.last_heartbeat = None
        
        # 메시지 배치 처리
        self.message_buffer = []
        self.batch_size = 10
        self.batch_timeout = 100  # milliseconds
    
    async def connect(self):
        """
        WebSocket 연결 시 호출
        """
        try:
            # URL 파라미터에서 채팅방 정보 추출
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'
            
            # 🔧 수정: 쿼리 파라미터에서 사용자 정보 추출
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            query_params = {}
            if query_string:
                for param in query_string.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = value
            
            user_id = query_params.get('user_id')
            user_email = query_params.get('user_email')
            
            logger.info(f"🔍 쿼리 파라미터: user_id={user_id}, user_email={user_email}")
            
            # 🔧 수정: 전달받은 사용자 정보로 실제 사용자 찾기
            if user_id or user_email:
                self.user = await self._get_user_by_params(user_id, user_email)
                if not self.user:
                    logger.error(f"사용자를 찾을 수 없음: user_id={user_id}, user_email={user_email}")
                    await self.close()
                    return
            else:
                logger.error("사용자 정보가 제공되지 않음")
                await self.close()
                return
            
            # 채팅방 생성 또는 가져오기
            self.chat_room = await self._get_or_create_chat_room()
            if not self.chat_room:
                logger.error(f"채팅방 생성/조회 실패: {self.room_name}")
                await self.close()
                return
            
            # 채팅방 그룹에 참여
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # 연결 수락
            await self.accept()
            self.is_connected = True
            
            # 연결 정보 저장
            await self._create_connection_record()
            
            # 🔧 추가: 연결 직후 사용자 정보 전송
            await self._send_user_info()
            
            logger.info(f"✅ WebSocket 연결 성공: {self.user.user_id} -> {self.room_name}")
            
        except Exception as e:
            logger.error(f"WebSocket 연결 오류: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """
        WebSocket 연결 해제 시 호출
        """
        try:
            # 연결 상태 업데이트
            self.is_connected = False
            
            # 연결 기록 업데이트
            if self.connection_id:
                await self._update_connection_record()
            
            # 채팅방 그룹에서 나가기
            if self.room_group_name:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            
            logger.info(f"🔌 WebSocket 연결 해제: {self.user.user_id if self.user else 'unknown'} (코드: {close_code})")
            
        except Exception as e:
            logger.error(f"WebSocket 연결 해제 오류: {e}")
    
    async def receive(self, text_data):
        """
        클라이언트로부터 메시지 수신
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            logger.info(f"📨 메시지 수신: {message_type} from {self.user.user_id if self.user else 'unknown'}")
            
            # 메시지 타입별 처리
            if message_type == 'chat_message' or message_type == 'message':
                await self._handle_chat_message(data)
            elif message_type == 'heartbeat':
                await self._handle_heartbeat(data)
            elif message_type == 'typing_start':
                await self._handle_typing_start(data)
            elif message_type == 'typing_stop':
                await self._handle_typing_stop(data)
            elif message_type == 'mark_read':
                await self._handle_mark_read(data)
            elif message_type == 'get_history':
                await self._handle_get_history(data)
            elif message_type == 'add_reaction':
                await self._handle_add_reaction(data)
            elif message_type == 'remove_reaction':
                await self._handle_remove_reaction(data)
            elif message_type == 'sync_latest':
                await self._handle_sync_latest(data)
            elif message_type == 'request_history':
                await self._handle_request_history(data)
            else:
                logger.warning(f"알 수 없는 메시지 타입: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
    
    # 🔧 추가: 사용자 정보 전송
    async def _send_user_info(self):
        """연결된 사용자 정보를 클라이언트에 전송"""
        try:
            # 클럽 관리자 여부 확인
            is_admin = await self._check_club_admin()
            
            user_info_data = {
                'type': 'user_info',
                'user_id': self.user.user_id,
                'user_name': self.user.name,
                'display_name': getattr(self.user, 'display_name', self.user.name),
                'is_admin': is_admin,
                'connection_suffix': str(datetime.now().microsecond)[:6]
            }
            
            logger.info(f"📨 USER_INFO 메시지 전송: {user_info_data}")
            
            await self.send(text_data=json.dumps(user_info_data))
            
        except Exception as e:
            logger.error(f"사용자 정보 전송 오류: {e}")
    
    @database_sync_to_async
    def _check_club_admin(self):
        """클럽 관리자 여부 확인"""
        try:
            if self.chat_room and self.chat_room.chat_room_type == 'CLUB' and self.chat_room.club_id:
                from clubs.models import Club, ClubMember
                club = Club.objects.get(id=self.chat_room.club_id)
                club_member = ClubMember.objects.get(user=self.user, club=club)
                is_admin = club_member.role == "admin"
                logger.info(f"🔍 클럽 관리자 확인: 사용자={self.user.user_id}, 클럽={club.id}, 역할={club_member.role}, 관리자={is_admin}")
                return is_admin
            else:
                # 일반 채팅방의 경우
                from .models import ChatRoomParticipant
                participant = ChatRoomParticipant.objects.filter(
                    chat_room=self.chat_room,
                    user=self.user,
                    is_active=True
                ).first()
                is_admin = participant and participant.role in ['ADMIN', 'MODERATOR']
                logger.info(f"🔍 일반 채팅방 관리자 확인: 사용자={self.user.user_id}, 관리자={is_admin}")
                return is_admin
        except Exception as e:
            logger.error(f"관리자 확인 오류: {e}")
            return False
    
    async def _handle_chat_message(self, data):
        """채팅 메시지 처리"""
        try:
            content = data.get('content', '').strip()
            if not content:
                return
            
            message_type = data.get('message_type', 'TEXT')
            
            # 메시지 저장
            message = await self._save_message(content, message_type)
            if not message:
                return
            
            logger.info(f"💬 메시지 저장: {self.user.name} -> {content[:50]}...")
            
            # 그룹에 메시지 브로드캐스트
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': str(message.id),  # 🔧 수정: UUID를 문자열로 변환
                        'content': message.content,
                        'sender': message.sender.name,
                        'sender_id': message.sender.user_id,  # 🔧 수정: 기존 데이터와 호환되는 user_id 사용
                        'sender_name': message.sender.name,
                        'message_type': message.message_type,
                        'created_at': message.created_at.isoformat(),
                        'is_pinned': message.is_pinned,
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"채팅 메시지 처리 오류: {e}")
    
    async def _handle_heartbeat(self, data):
        """하트비트 처리"""
        try:
            self.last_heartbeat = datetime.now()
            
            await self.send(text_data=json.dumps({
                'type': 'heartbeat_ack',
                'timestamp': datetime.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"하트비트 처리 오류: {e}")
    
    async def _handle_typing_start(self, data):
        """타이핑 시작 처리"""
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_name': self.user.name,
                    'is_typing': True,
                    'timestamp': datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"타이핑 시작 처리 오류: {e}")
    
    async def _handle_typing_stop(self, data):
        """타이핑 중단 처리"""
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_name': self.user.name,
                    'is_typing': False,
                    'timestamp': datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"타이핑 중단 처리 오류: {e}")
    
    async def _handle_mark_read(self, data):
        """메시지 읽음 처리"""
        try:
            message_id = data.get('message_id')
            if message_id:
                await self._mark_message_read(message_id)
        except Exception as e:
            logger.error(f"메시지 읽음 처리 오류: {e}")
    
    async def _handle_get_history(self, data):
        """채팅 히스토리 조회"""
        try:
            limit = data.get('limit', 50)
            offset = data.get('offset', 0)
            
            messages = await self._get_chat_history(limit, offset)
            
            await self.send(text_data=json.dumps({
                'type': 'message_history',
                'messages': messages
            }))
            
        except Exception as e:
            logger.error(f"채팅 히스토리 조회 오류: {e}")
    
    async def _handle_add_reaction(self, data):
        """반응 추가 처리"""
        try:
            message_id = data.get('message_id')
            emoji = data.get('emoji')
            
            if message_id and emoji:
                reaction = await self._add_reaction(message_id, emoji)
                if reaction:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'reaction_update',
                            'message_id': message_id,
                            'emoji': emoji,
                            'user_name': self.user.name,
                            'action': 'add',
                            'timestamp': datetime.now().isoformat()
                        }
                    )
        except Exception as e:
            logger.error(f"반응 추가 처리 오류: {e}")
    
    async def _handle_remove_reaction(self, data):
        """반응 제거 처리"""
        try:
            message_id = data.get('message_id')
            emoji = data.get('emoji')
            
            if message_id and emoji:
                removed = await self._remove_reaction(message_id, emoji)
                if removed:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'reaction_update',
                            'message_id': message_id,
                            'emoji': emoji,
                            'user_name': self.user.name,
                            'action': 'remove',
                            'timestamp': datetime.now().isoformat()
                        }
                    )
        except Exception as e:
            logger.error(f"반응 제거 처리 오류: {e}")
    
    async def _handle_sync_latest(self, data):
        """최신 메시지 동기화"""
        try:
            last_message_id = data.get('last_message_id')
            messages = await self._get_messages_after(last_message_id)
            
            if messages:
                await self.send(text_data=json.dumps({
                    'type': 'sync_latest_response',
                    'messages': messages
                }))
                
        except Exception as e:
            logger.error(f"최신 메시지 동기화 오류: {e}")
    
    async def _handle_request_history(self, data):
        """채팅 히스토리 요청 처리"""
        try:
            # 최근 메시지 조회 (기본 50개)
            limit = data.get('limit', 50)
            messages = await self._get_recent_messages(limit=limit)
            
            if messages:
                await self.send(text_data=json.dumps({
                    'type': 'message_history',
                    'messages': messages
                }))
                logger.info(f"채팅 히스토리 {len(messages)}개 전송 완료")
            else:
                await self.send(text_data=json.dumps({
                    'type': 'message_history',
                    'messages': []
                }))
                logger.info("채팅 히스토리가 비어있습니다")
                
        except Exception as e:
            logger.error(f"채팅 히스토리 요청 처리 오류: {e}")
    
    # 그룹 메시지 핸들러들
    async def chat_message(self, event):
        """채팅 메시지 브로드캐스트"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        """타이핑 표시기 브로드캐스트"""
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'user_name': event['user_name'],
            'is_typing': event['is_typing'],
            'timestamp': event['timestamp']
        }))
    
    async def reaction_update(self, event):
        """반응 업데이트 브로드캐스트"""
        await self.send(text_data=json.dumps({
            'type': 'reaction_update',
            'message_id': event['message_id'],
            'emoji': event['emoji'],
            'user_name': event['user_name'],
            'action': event['action'],
            'timestamp': event['timestamp']
        }))
    
    # 데이터베이스 작업 메서드들
    @database_sync_to_async
    def _get_user_by_params(self, user_id, user_email):
        """파라미터로 사용자 조회"""
        try:
            User = get_user_model()
            
            # user_id로 먼저 조회 시도
            if user_id:
                try:
                    return User.objects.get(id=int(user_id))
                except (User.DoesNotExist, ValueError):
                    pass
            
            # user_email로 조회 시도
            if user_email:
                try:
                    return User.objects.get(email=user_email)
                except User.DoesNotExist:
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"사용자 조회 오류: {e}")
            return None
    
    @database_sync_to_async
    def _get_or_create_chat_room(self):
        """채팅방 생성 또는 조회"""
        try:
            # 채팅방 이름 파싱 (예: event_123, club_456)
            if self.room_name.startswith('event_'):
                event_id = self.room_name.replace('event_', '')
                chat_room, created = ChatRoom.objects.get_or_create(
                    event_id=event_id,
                    defaults={
                        'chat_room_name': f'이벤트 {event_id} 채팅방',
                        'chat_room_type': 'EVENT'
                    }
                )
            elif self.room_name.startswith('club_'):
                club_id = self.room_name.replace('club_', '')
                chat_room, created = ChatRoom.objects.get_or_create(
                    club_id=club_id,
                    defaults={
                        'chat_room_name': f'클럽 {club_id} 채팅방',
                        'chat_room_type': 'CLUB'
                    }
                )
            else:
                # 일반 채팅방 (room_name이 숫자면 클럽 ID로 처리)
                try:
                    club_id = int(self.room_name)
                    chat_room, created = ChatRoom.objects.get_or_create(
                        club_id=club_id,
                        defaults={
                            'chat_room_name': f'클럽 {club_id} 채팅방',
                            'chat_room_type': 'CLUB'
                        }
                    )
                except ValueError:
                    # 숫자가 아니면 일반 채팅방
                    chat_room, created = ChatRoom.objects.get_or_create(
                        chat_room_name=self.room_name,
                        defaults={'chat_room_type': 'GENERAL'}
                    )
            
            # 참가자 추가
            ChatRoomParticipant.objects.get_or_create(
                chat_room=chat_room,
                user=self.user
            )
            
            return chat_room
            
        except Exception as e:
            logger.error(f"채팅방 생성/조회 오류: {e}")
            return None
    
    @database_sync_to_async
    def _create_connection_record(self):
        """연결 기록 생성"""
        try:
            connection = ChatConnection.objects.create(
                user=self.user,
                chat_room=self.chat_room,
                connection_id=self.channel_name,  # channel_name을 connection_id로 사용
                connected_at=timezone.now()
            )
            self.connection_id = connection.id
            
        except Exception as e:
            logger.error(f"연결 기록 생성 오류: {e}")
    
    @database_sync_to_async
    def _update_connection_record(self):
        """연결 기록 업데이트"""
        try:
            if self.connection_id:
                ChatConnection.objects.filter(id=self.connection_id).update(
                    disconnected_at=timezone.now()
                )
        except Exception as e:
            logger.error(f"연결 기록 업데이트 오류: {e}")
    
    @database_sync_to_async
    def _save_message(self, content, message_type='TEXT'):
        """메시지 저장"""
        try:
            message = ChatMessage.objects.create(
                chat_room=self.chat_room,
                sender=self.user,
                content=content,
                message_type=message_type,
                created_at=timezone.now()
            )
            return message
            
        except Exception as e:
            logger.error(f"메시지 저장 오류: {e}")
            return None
    
    @database_sync_to_async
    def _mark_message_read(self, message_id):
        """메시지 읽음 처리"""
        try:
            message = ChatMessage.objects.get(id=message_id)
            read_status, created = MessageReadStatus.objects.get_or_create(
                message=message,
                user=self.user,
                defaults={'read_at': timezone.now()}
            )
            return read_status
            
        except Exception as e:
            logger.error(f"메시지 읽음 처리 오류: {e}")
            return None
    
    @database_sync_to_async
    def _get_chat_history(self, limit=50, offset=0):
        """채팅 히스토리 조회"""
        try:
            messages = ChatMessage.objects.filter(
                chat_room=self.chat_room
            ).select_related('sender').order_by('-created_at')[offset:offset+limit]
            
            return [{
                'id': msg.id,
                'content': msg.content,
                'sender': msg.sender.name,
                'sender_id': msg.sender.user_id if msg.sender.user_id else "unknown",
                'sender_name': msg.sender.name,
                'message_type': msg.message_type,
                'created_at': msg.created_at.isoformat(),
                'is_pinned': msg.is_pinned,
            } for msg in reversed(messages)]
            
        except Exception as e:
            logger.error(f"채팅 히스토리 조회 오류: {e}")
            return []
    
    @database_sync_to_async
    def _add_reaction(self, message_id, emoji):
        """반응 추가"""
        try:
            message = ChatMessage.objects.get(id=message_id)
            reaction, created = ChatReaction.objects.get_or_create(
                message=message,
                user=self.user,
                emoji=emoji
            )
            return reaction
            
        except Exception as e:
            logger.error(f"반응 추가 오류: {e}")
            return None
    
    @database_sync_to_async
    def _remove_reaction(self, message_id, emoji):
        """반응 제거"""
        try:
            ChatReaction.objects.filter(
                message_id=message_id,
                user=self.user,
                emoji=emoji
            ).delete()
            return True
            
        except Exception as e:
            logger.error(f"반응 제거 오류: {e}")
            return False
    
    @database_sync_to_async
    def _get_messages_after(self, last_message_id):
        """특정 메시지 이후의 메시지들 조회"""
        try:
            if not last_message_id:
                return []
                
            messages = ChatMessage.objects.filter(
                chat_room=self.chat_room,
                id__gt=last_message_id
            ).select_related('sender').order_by('created_at')
            
            return [{
                'id': msg.id,
                'content': msg.content,
                'sender': msg.sender.name,
                'sender_id': msg.sender.user_id if msg.sender.user_id else "unknown",
                'sender_name': msg.sender.name,
                'message_type': msg.message_type,
                'created_at': msg.created_at.isoformat(),
                'is_pinned': msg.is_pinned,
            } for msg in messages]
            
        except Exception as e:
            logger.error(f"최신 메시지 조회 오류: {e}")
            return []
    
    async def _send_existing_messages_async(self):
        """기존 메시지들을 비동기로 전송"""
        try:
            messages = await self._get_recent_messages()
            
            if messages:
                # 메시지들을 배치로 전송
                batch_data = {
                    'type': 'MESSAGE_HISTORY_BATCH',
                    'messages': []
                }
                
                for message in messages:
                    sender_id = message.sender.user_id if message.sender.user_id else "unknown"
                    
                    logger.info(f"🔍 메시지 {message.id}: sender={message.sender.email}, sender_id={sender_id}, sender_name={message.sender.name}")
                    
                    batch_data['messages'].append({
                        'id': message.id,
                        'sender': message.sender.name,
                        'sender_id': sender_id,
                        'content': message.content,
                        'message_type': message.message_type,
                        'created_at': message.created_at.isoformat(),
                        'is_pinned': getattr(message, 'is_pinned', False)
                    })
                
                logger.info(f"📦 배치 메시지 전송: {len(batch_data['messages'])}개")
                await self.send(text_data=json.dumps(batch_data))
                
        except Exception as e:
            logger.error(f"기존 메시지 전송 오류: {e}")
    
    @database_sync_to_async
    def _get_recent_messages(self, limit=50):
        """최근 메시지들 조회 (JSON 직렬화 가능한 형태로)"""
        try:
            messages = ChatMessage.objects.filter(
                chat_room=self.chat_room
            ).select_related('sender').order_by('-created_at')[:limit]
            
            # JSON 직렬화 가능한 딕셔너리 리스트로 변환
            message_list = []
            for msg in reversed(messages):
                message_list.append({
                    'id': str(msg.id),
                    'sender': msg.sender.name,
                    'sender_id': msg.sender.user_id if msg.sender.user_id else "unknown",
                    'sender_name': msg.sender.name,
                    'content': msg.content,
                    'message_type': msg.message_type,
                    'created_at': msg.created_at.isoformat(),
                    'is_pinned': getattr(msg, 'is_pinned', False),
                    'is_announcement': getattr(msg, 'is_announcement', False),
                })
            
            return message_list
            
        except Exception as e:
            logger.error(f"최근 메시지 조회 오류: {e}")
            return []