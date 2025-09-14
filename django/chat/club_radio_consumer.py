# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
import json
import logging
import asyncio
import os
import subprocess
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from datetime import datetime, timedelta
from .services.ai_commentary_generator import ai_commentary_generator

logger = logging.getLogger(__name__)

class ClubRadioConsumer(AsyncWebsocketConsumer):
    """
    🎵 클럽별 라디오 Consumer
    - 각 클럽의 가장 최근 이벤트 기준으로 라디오 운영
    - 클럽별 동기화된 스트림 제공
    - AI 중계멘트 자동 생성 및 재생
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.club_id = None
        self.is_connected = False
        self.room_group_name = None
        
        # 배경음악 파일 경로
        self.background_music_file = os.path.join(
            settings.BASE_DIR, 'static', 'pga2021_main3.mp3'
        )
        
        # HLS 스트림 디렉토리
        self.stream_dir = os.path.join(settings.BASE_DIR, 'static', 'hls', 'club_radio')
        
        # FFmpeg 프로세스
        self.ffmpeg_process = None
        self.is_streaming = False
        
    async def connect(self):
        """WebSocket 연결"""
        try:
            self.club_id = self.scope['url_route']['kwargs']['club_id']
            self.room_group_name = f'radio_club_{self.club_id}'
            
            # 클럽 ID 검증
            if not self.club_id:
                await self.close()
                return
                
            await self.accept()
            self.is_connected = True
            
            # 클럽 라디오 그룹에 참가
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # 연결 확인 메시지 전송
            await self.send(text_data=json.dumps({
                'type': 'club_radio_connected',
                'message': f'클럽 {self.club_id} 라디오에 연결되었습니다',
                'club_id': self.club_id
            }))
            
            logger.info(f"🎵 클럽 {self.club_id} 라디오 연결")
            
        except Exception as e:
            logger.error(f"클럽 라디오 연결 오류: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """WebSocket 연결 해제"""
        try:
            self.is_connected = False
            
            # 클럽 라디오 그룹에서 나가기
            if self.room_group_name:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            
            logger.info(f"🔌 클럽 {self.club_id} 라디오 연결 해제 (코드: {close_code})")
            
        except Exception as e:
            logger.error(f"클럽 라디오 연결 해제 오류: {e}")
    
    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            logger.info(f"📨 클럽 라디오 메시지 수신: {message_type} from club_{self.club_id}")
            
            if message_type == 'start_club_radio':
                await self._handle_start_club_radio(data)
            elif message_type == 'stop_club_radio':
                await self._handle_stop_club_radio(data)
            elif message_type == 'get_club_stream_info':
                await self._handle_get_club_stream_info(data)
            else:
                logger.warning(f"알 수 없는 클럽 라디오 메시지 타입: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"클럽 라디오 메시지 처리 오류: {e}")
    
    async def _handle_start_club_radio(self, data):
        """클럽 라디오 시작 처리"""
        try:
            # HLS 스트림 시작
            if not self.is_streaming:
                await self._start_hls_stream()
            
            # HLS URL 전송
            hls_url = f"http://localhost:8000/static/hls/club_radio/club_{self.club_id}/playlist.m3u8"
            
            await self.send(text_data=json.dumps({
                'type': 'hls_stream_url',
                'url': hls_url,
                'club_id': self.club_id,
                'message': f'클럽 {self.club_id} 라디오 스트림을 시작합니다'
            }))
            
            logger.info(f"🎵 클럽 {self.club_id} HLS 스트림 URL 전송: {hls_url}")
            
        except Exception as e:
            logger.error(f"클럽 라디오 시작 처리 오류: {e}")
    
    async def _handle_stop_club_radio(self, data):
        """클럽 라디오 중단 처리"""
        try:
            # HLS 스트림 중단
            if self.is_streaming:
                await self._stop_hls_stream()
            
            await self.send(text_data=json.dumps({
                'type': 'club_radio_stopped',
                'club_id': self.club_id,
                'message': f'클럽 {self.club_id} 라디오가 중단되었습니다'
            }))
            
            logger.info(f"🛑 클럽 {self.club_id} 라디오 중단")
            
        except Exception as e:
            logger.error(f"클럽 라디오 중단 처리 오류: {e}")
    
    async def _handle_get_club_stream_info(self, data):
        """클럽 스트림 정보 요청 처리"""
        try:
            # 현재 재생 위치와 상태 정보 전송
            stream_info = {
                'type': 'club_stream_info',
                'club_id': self.club_id,
                'is_streaming': self.is_streaming,
                'hls_url': f"http://localhost:8000/static/hls/club_radio/club_{self.club_id}/playlist.m3u8",
                'timestamp': datetime.now().isoformat()
            }
            
            await self.send(text_data=json.dumps(stream_info))
            
        except Exception as e:
            logger.error(f"클럽 스트림 정보 처리 오류: {e}")
    
    async def _start_hls_stream(self):
        """HLS 스트림 시작"""
        try:
            if self.is_streaming:
                return
            
            # 스트림 디렉토리 생성
            stream_club_dir = os.path.join(self.stream_dir, f'club_{self.club_id}')
            os.makedirs(stream_club_dir, exist_ok=True)
            
            # FFmpeg 명령어로 HLS 스트림 생성
            command = [
                'ffmpeg',
                '-i', self.background_music_file,
                '-c:a', 'aac',
                '-b:a', '128k',
                '-f', 'hls',
                '-hls_time', '2',  # 2초 세그먼트
                '-hls_list_size', '10',  # 10개 세그먼트 유지
                '-hls_flags', 'delete_segments+append_list',
                '-hls_segment_filename', os.path.join(stream_club_dir, 'segment_%03d.ts'),
                os.path.join(stream_club_dir, 'playlist.m3u8')
            ]
            
            # FFmpeg 프로세스 시작
            self.ffmpeg_process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.is_streaming = True
            logger.info(f"🎵 클럽 {self.club_id} HLS 스트림 시작")
            
        except Exception as e:
            logger.error(f"클럽 {self.club_id} HLS 스트림 시작 오류: {e}")
    
    async def _stop_hls_stream(self):
        """HLS 스트림 중단"""
        try:
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                await self.ffmpeg_process.wait()
                self.ffmpeg_process = None
            
            self.is_streaming = False
            logger.info(f"🛑 클럽 {self.club_id} HLS 스트림 중단")
            
        except Exception as e:
            logger.error(f"클럽 {self.club_id} HLS 스트림 중단 오류: {e}")
    
    async def start_background_music(self, event):
        """배경음악 시작 (자동 스케줄러에서 호출)"""
        try:
            club_id = event['club_id']
            event_id = event['event_id']
            message = event['message']
            
            await self.send(text_data=json.dumps({
                'type': 'start_background_music',
                'club_id': club_id,
                'event_id': event_id,
                'message': message
            }))
            
            logger.info(f"🎵 클럽 {club_id} 배경음악 시작: {message}")
            
        except Exception as e:
            logger.error(f"배경음악 시작 오류: {e}")
    
    async def play_commentary(self, event):
        """중계멘트 재생 처리 (자동 스케줄러에서 호출)"""
        try:
            from events.models import Event
            
            club_id = event['club_id']
            event_id = event['event_id']
            text = event['text']
            commentary_type = event.get('commentary_type', 'regular')
            commentary_count = event.get('commentary_count', 1)
            
            # AI로 오디오 생성
            if commentary_type == 'opening':
                _, audio_data = await ai_commentary_generator.generate_opening_commentary(
                    Event.objects.get(id=event_id)
                )
            else:
                _, audio_data = await ai_commentary_generator.generate_regular_commentary(
                    Event.objects.get(id=event_id), commentary_count
                )
            
            if audio_data:
                # Base64로 인코딩
                audio_base64 = ai_commentary_generator.text_to_base64(audio_data)
                
                # 클라이언트에 전송
                await self.send(text_data=json.dumps({
                    'type': 'commentary_audio',
                    'club_id': club_id,
                    'event_id': event_id,
                    'audio_data': audio_base64,
                    'text': text,
                    'commentary_type': commentary_type,
                    'message': f'{commentary_type} 중계멘트를 재생합니다'
                }))
                
                logger.info(f"🎤 클럽 {club_id} AI 중계멘트 재생: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"클럽 {self.club_id} AI 중계멘트 재생 오류: {e}")
    
    async def radio_stopped(self, event):
        """라디오 중단 처리"""
        try:
            club_id = event['club_id']
            event_id = event['event_id']
            message = event['message']
            
            await self.send(text_data=json.dumps({
                'type': 'radio_stopped',
                'club_id': club_id,
                'event_id': event_id,
                'message': message
            }))
            
        except Exception as e:
            logger.error(f"라디오 중단 처리 오류: {e}")
"""
