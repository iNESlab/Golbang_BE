# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
RTMP 기반 라디오 WebSocket Consumer
nginx-rtmp 미디어 서버와 연동하여 안정적인 라이브 스트리밍을 제공합니다.
"""
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from events.models import Event
from django.utils import timezone
from datetime import timedelta
from .services.rtmp_broadcast_service import rtmp_broadcast_service

logger = logging.getLogger(__name__)

class RTMPRadioConsumer(AsyncWebsocketConsumer):
    """
    🎵 RTMP 기반 라디오 Consumer
    - nginx-rtmp 미디어 서버 사용
    - 클럽별 독립적인 방송 스트림
    - 안정적인 HLS 스트리밍 제공
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.club_id = None
        self.is_connected = False
        self.room_group_name = None
    
    async def connect(self):
        """WebSocket 연결"""
        try:
            # URL에서 club_id 추출
            self.club_id = int(self.scope['url_route']['kwargs']['club_id'])
            self.room_group_name = f'radio_club_{self.club_id}'
            
            logger.info(f"🔌 라디오 연결 시도: 클럽 {self.club_id}")
            
            # 현재 진행중인 이벤트 확인
            event = await self._get_active_event()
            if not event:
                logger.warning(f"클럽 {self.club_id}에 진행 중인 이벤트가 없습니다")
                await self.close(code=4001)  # 커스텀 에러 코드
                return
            
            # 방송 시간 확인
            if not self._is_within_broadcast_window(event):
                logger.warning(f"이벤트 {event.id}가 방송 시간 범위에 없습니다")
                await self.close(code=4002)
                return
            
            # WebSocket 그룹 참여
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # 연결 승인
            await self.accept()
            self.is_connected = True
            
            # 방송 시작 (이미 시작된 경우 무시됨)
            broadcast_started = await rtmp_broadcast_service.start_club_broadcast(self.club_id)
            
            if broadcast_started:
                # 클라이언트에게 스트림 정보 전송
                hls_url = rtmp_broadcast_service.get_hls_url(self.club_id)
                broadcast_status = await rtmp_broadcast_service.get_broadcast_status(self.club_id)
                
                await self.send(text_data=json.dumps({
                    'type': 'stream_info',
                    'hls_url': hls_url,
                    'status': broadcast_status,
                    'message': f'클럽 {self.club_id} 라디오에 연결되었습니다'
                }))
                
                logger.info(f"✅ 클럽 {self.club_id} 라디오 연결 완료")
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '방송을 시작할 수 없습니다'
                }))
                await self.close(code=4003)
                
        except ValueError:
            logger.error("잘못된 club_id 형식")
            await self.close(code=4000)
        except Exception as e:
            logger.error(f"라디오 연결 오류: {e}")
            await self.close(code=4999)
    
    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        try:
            if self.is_connected and self.room_group_name:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            
            logger.info(f"👋 클럽 {self.club_id} 라디오 연결 해제 (코드: {close_code})")
            
        except Exception as e:
            logger.error(f"라디오 연결 해제 오류: {e}")
    
    async def receive(self, text_data):
        """클라이언트 메시지 수신"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_status':
                # 방송 상태 조회
                status = await rtmp_broadcast_service.get_broadcast_status(self.club_id)
                await self.send(text_data=json.dumps({
                    'type': 'status_response',
                    'status': status
                }))
                
            elif message_type == 'ping':
                # 연결 유지용 핑
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
                
            else:
                logger.warning(f"알 수 없는 메시지 타입: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("잘못된 JSON 형식")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")
    
    # 그룹 메시지 핸들러들
    async def commentary_started(self, event):
        """해설 시작 알림"""
        await self.send(text_data=json.dumps({
            'type': 'commentary_started',
            'message': event['message']
        }))
    
    async def commentary_ended(self, event):
        """해설 종료 알림"""
        await self.send(text_data=json.dumps({
            'type': 'commentary_ended',
            'message': event['message']
        }))
    
    async def broadcast_status_update(self, event):
        """방송 상태 업데이트"""
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status']
        }))
    
    async def broadcast_error(self, event):
        """방송 오류 알림"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': event['message']
        }))
    
    # 헬퍼 메서드들
    async def _get_active_event(self) -> Event:
        """클럽의 현재 진행중인 이벤트 조회"""
        try:
            now = timezone.now()
            event = await database_sync_to_async(
                lambda: Event.objects.filter(
                    club_id=self.club_id,
                    start_date_time__lte=now + timedelta(minutes=30),  # 30분 전부터
                    end_date_time__gte=now  # 아직 끝나지 않음
                ).order_by('-start_date_time').first()
            )()
            
            return event
        except Exception as e:
            logger.error(f"❌ 클럽 {self.club_id} 활성 이벤트 조회 오류: {e}")
            return None
    
    def _is_within_broadcast_window(self, event: Event) -> bool:
        """방송 가능 시간인지 확인"""
        now = timezone.now()
        broadcast_start = event.start_date_time - timedelta(minutes=30)
        broadcast_end = event.end_date_time
        
        return broadcast_start <= now <= broadcast_end
"""
