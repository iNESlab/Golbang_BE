# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from events.models import Event
from django.utils import timezone
from datetime import timedelta
from .services.rtmp_broadcast_service import rtmp_broadcast_service

logger = logging.getLogger(__name__)

class SynchronizedRadioConsumer(AsyncWebsocketConsumer):
    """
    🎵 RTMP 기반 동기화된 라디오 Consumer
    - nginx-rtmp 미디어 서버 사용
    - 클럽별 독립적인 방송 스트림
    - 안정적인 HLS 스트리밍 제공
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.club_id = None
        self.is_connected = False
        self.room_group_name = None
        
        if not self.background_music_file:
            logger.warning("배경음악 파일을 찾을 수 없습니다. 기본 파일을 생성합니다.")
            # 기본 배경음악 파일 생성 (빈 파일)
            self.background_music_file = os.path.join(settings.BASE_DIR, 'static', 'default_music.mp3')
            if not os.path.exists(self.background_music_file):
                os.makedirs(os.path.dirname(self.background_music_file), exist_ok=True)
                with open(self.background_music_file, 'w') as f:
                    f.write('')  # 빈 파일 생성
        
        # stream_dir 는 connect 에서 event_id 확인 후 설정
        
        # FFmpeg 프로세스
        self.ffmpeg_process = None
        self.is_streaming = False
        
        # 서버 IP 주소 (localhost 사용)
        self.server_ip = 'localhost'
        
    async def connect(self):
        """WebSocket 연결"""
        try:
            self.club_id = self.scope['url_route']['kwargs']['club_id']

            # 최신/진행중 이벤트 찾기
            latest_event = await self._get_current_event(self.club_id)
            if not latest_event:
                logger.warning(f"클럽 {self.club_id}에 진행 중인 이벤트가 없습니다")
                await self.close()
                return
            self.event_id = latest_event.id
            self.room_group_name = f'radio_club_{self.club_id}'

            # 이벤트 상태/시간창 검사 (시작 30분 전 ~ 종료)
            try:
                event = await database_sync_to_async(Event.objects.get)(id=self.event_id)
                from django.utils import timezone
                from datetime import timedelta
                now = timezone.now()
                allowed = now >= (event.start_date_time - timedelta(minutes=30))
                if not allowed:
                    logger.warning(f"이벤트 {self.event_id} 방송 가능 시간이 아님 – 연결 거부")
                    await self.close()
                    return
            except Event.DoesNotExist:
                logger.error(f"이벤트 {self.event_id} 존재하지 않음 – 연결 거부")
                await self.close()
                return

            # HLS 스트림 디렉토리 (클럽별)
            self.stream_dir = os.path.join(settings.BASE_DIR, 'static', 'hls', 'radio', f'club_{self.club_id}')
            os.makedirs(self.stream_dir, exist_ok=True)
            
            # 중복 연결 방지 로그
            logger.info(f"🔌 동기화 라디오 연결 시도: 이벤트 {self.event_id}, 채널 {self.channel_name}")
            
            # 이벤트 ID 검증
            if not self.event_id:
                await self.close()
                return
                
            await self.accept()
            self.is_connected = True
            
            # 라디오 그룹에 참가
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            logger.info(f"🎵 라디오 그룹 참가: {self.room_group_name}, 채널: {self.channel_name}")
            logger.info(f"🎵 Consumer 연결 완료: 이벤트 {self.event_id}")
            
            # 연결 확인 메시지 전송
            await self.send(text_data=json.dumps({
                'type': 'radio_connected',
                'message': f'이벤트 {self.event_id} 라디오에 연결되었습니다',
                'event_id': self.event_id
            }))
            
            # 이벤트 방송 서비스 시작 (club 기반)
            from chat.services.event_broadcast_service import event_broadcast_service
            await event_broadcast_service.start_event_broadcast(int(self.event_id))
            
            logger.info(f"🎵 이벤트 {self.event_id} 라디오 연결")
            
        except Exception as e:
            logger.error(f"라디오 연결 오류: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """클라이언트 연결이 끊어져도 방송 스트림은 유지한다."""
        try:
            self.is_connected = False
            if self.room_group_name:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            
            event_id = getattr(self, 'event_id', 'N/A')
            logger.info("👋 Client disconnected from radio for event %s. Broadcast continues.", event_id)

            # 중요: 개별 클라이언트의 연결 해제가 전체 방송을 중단시키지 않도록 함.
            # 방송 종료는 EventBroadcastService가 이벤트 종료 시간에 맞춰 처리.
            # from chat.services.event_broadcast_service import event_broadcast_service
            # await event_broadcast_service.stop_event_broadcast(int(self.event_id))
            # from chat.services.hls_service import HLSService
            # hls_service = HLSService()
            # await hls_service.stop_stream(int(self.club_id))
            
        except Exception as e:
            logger.error(f"라디오 연결 해제 오류: {e}")
    
    async def _force_cleanup_ffmpeg(self):
        """시스템 레벨에서 FFmpeg 프로세스 강제 정리"""
        try:
            import psutil
            import signal
            
            # 현재 이벤트의 HLS 디렉토리 경로
            target_path = f"club_{self.club_id}"
            
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'ffmpeg' and proc.info['cmdline']:
                        cmdline_str = ' '.join(proc.info['cmdline'])
                        if target_path in cmdline_str:
                            logger.warning(f"🔥 강제 종료: FFmpeg PID {proc.info['pid']}")
                            proc.send_signal(signal.SIGTERM)
                            killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed_count > 0:
                logger.info(f"🧹 FFmpeg 프로세스 {killed_count}개 강제 종료됨")
            else:
                logger.debug("🔍 정리할 FFmpeg 프로세스 없음")
                
        except ImportError:
            logger.warning("⚠️ psutil 모듈 없음. 시스템 레벨 정리 생략")
        except Exception as e:
            logger.error(f"FFmpeg 강제 정리 오류: {e}")
    
    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            logger.info(f"📨 라디오 메시지 수신: {message_type} from event_{self.event_id}")
            
            if message_type == 'start_radio':
                await self._handle_start_radio(data)
            elif message_type == 'stop_radio':
                await self._handle_stop_radio(data)
            elif message_type == 'get_stream_info':
                await self._handle_get_stream_info(data)
            else:
                logger.warning(f"알 수 없는 라디오 메시지 타입: {message_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"라디오 메시지 처리 오류: {e}")
    
    async def _handle_start_radio(self, data):
        """라디오 시작 처리"""
        try:
            # HLS 스트림 시작
            if self.is_streaming:
                logger.warning(f"🎵 이벤트 {self.event_id} 이미 스트리밍 중 – 중복 요청 무시")
                return
            # HLS 스트림 시작 - 모니터링 시작
            if not self.is_streaming:
                await self._start_hls_stream()
            
            # HLS URL 전송 (동적 서버 IP 사용) - club 기반
            hls_url = f"http://{self.server_ip}:8000/static/hls/radio/club_{self.club_id}/playlist.m3u8"
            
            await self.send(text_data=json.dumps({
                'type': 'hls_stream_url',
                'url': hls_url,
                'event_id': self.event_id,
                'message': f'이벤트 {self.event_id} 라디오 스트림을 시작합니다'
            }))
            
            logger.info(f"🎵 이벤트 {self.event_id} HLS 스트림 URL 전송: {hls_url}")
            
        except Exception as e:
            logger.error(f"라디오 시작 처리 오류: {e}")
    
    async def _handle_stop_radio(self, data):
        """라디오 중단 처리"""
        try:
            # HLS 스트림 중단
            if self.is_streaming:
                await self._stop_hls_stream()
            
            await self.send(text_data=json.dumps({
                'type': 'radio_stopped',
                'event_id': self.event_id,
                'message': f'이벤트 {self.event_id} 라디오가 중단되었습니다'
            }))
            
            logger.info(f"🛑 이벤트 {self.event_id} 라디오 중단")
            
        except Exception as e:
            logger.error(f"라디오 중단 처리 오류: {e}")
    
    async def _handle_get_stream_info(self, data):
        """스트림 정보 요청 처리"""
        try:
            # 현재 재생 위치와 상태 정보 전송
            stream_info = {
                'type': 'stream_info',
                'event_id': self.event_id,
                'is_streaming': self.is_streaming,
                'hls_url': f"http://172.18.0.1:8000/static/hls/radio/event_{self.event_id}/playlist.m3u8",
                'timestamp': datetime.now().isoformat()
            }
            
            await self.send(text_data=json.dumps(stream_info))
            
        except Exception as e:
            logger.error(f"스트림 정보 처리 오류: {e}")
    
    async def _start_hls_stream(self):
        """HLS 스트림은 EventBroadcastService에서 관리됨 - 여기서는 모니터링만 시작"""
        try:
            if self.is_streaming:
                return

            # 기존 Consumer의 FFmpeg 프로세스 정리 (EventBroadcastService와 중복 방지)
            if self.ffmpeg_process:
                logger.info("🔄 Consumer FFmpeg 프로세스 종료 (EventBroadcastService 사용)")
                self.ffmpeg_process.terminate()
                try:
                    await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("⚠️ FFmpeg 프로세스 강제 종료")
                    self.ffmpeg_process.kill()
                    await self.ffmpeg_process.wait()
                self.ffmpeg_process = None

            # 스트림 디렉토리 확인 (club 기반)
            stream_event_dir = os.path.join(settings.BASE_DIR, 'static', 'hls', 'radio', f'club_{self.club_id}')
            
            # EventBroadcastService가 HLS 스트림을 관리하므로 여기서는 모니터링만 시작
            self.is_streaming = True
            logger.info(f"🎵 이벤트 {self.event_id} HLS 스트림 모니터링 시작 (EventBroadcastService 관리)")
            
            # playlist 모니터링 시작 (EventBroadcastService가 생성한 스트림 모니터링)
            asyncio.create_task(self._monitor_playlist(stream_event_dir))
            
        except Exception as e:
            logger.error(f"이벤트 {self.event_id} HLS 스트림 시작 오류: {e}")
    
    # AI 중계멘트 자동 생성 루프는 ClubRadioConsumer에서 처리하므로 제거
    
    def update_activity_time(self):
        """사용자 활동 시간 업데이트"""
        from django.utils import timezone
        self.last_activity_time = timezone.now()
        logger.info(f"📝 사용자 활동 감지: {self.last_activity_time}")
    
    async def _monitor_playlist(self, stream_event_dir):
        """playlist.m3u8 모니터링하여 세그먼트 번호 점프 감지"""
        playlist_path = os.path.join(stream_event_dir, 'playlist.m3u8')
        last_sequence = None
        last_segment_count = 0
        
        while self.is_streaming:
            try:
                if os.path.exists(playlist_path):
                    with open(playlist_path, 'r') as f:
                        content = f.read()
                    
                    # MEDIA-SEQUENCE 추출
                    import re
                    sequence_match = re.search(r'#EXT-X-MEDIA-SEQUENCE:(\d+)', content)
                    current_sequence = int(sequence_match.group(1)) if sequence_match else 0
                    
                    # 세그먼트 파일 개수 확인
                    segment_files = [f for f in os.listdir(stream_event_dir) if f.startswith('segment_') and f.endswith('.ts')]
                    current_segment_count = len(segment_files)
                    
                    # 점프 감지
                    if last_sequence is not None:
                        sequence_jump = current_sequence - last_sequence
                        segment_jump = current_segment_count - last_segment_count
                        
                        if sequence_jump > 5:  # 5 이상일 때만 경고
                            logger.warning(f"🚨 MEDIA-SEQUENCE 큰 점프 감지: {last_sequence} → {current_sequence} (점프: +{sequence_jump})")
                        
                        if segment_jump > 3:  # 3 이상일 때만 경고
                            logger.warning(f"🚨 세그먼트 파일 큰 점프 감지: {last_segment_count} → {current_segment_count} (점프: +{segment_jump})")
                        
                        # 정상적인 경우 로그
                        if sequence_jump == 1 and segment_jump == 1:
                            logger.debug(f"✅ 정상 진행: sequence={current_sequence}, segments={current_segment_count}")
                    
                    last_sequence = current_sequence
                    last_segment_count = current_segment_count
                
                await asyncio.sleep(1)  # 1초마다 체크
                
            except Exception as e:
                logger.error(f"playlist 모니터링 오류: {e}")
                await asyncio.sleep(5)
    
    async def _stop_hls_stream(self):
        """HLS 스트림 중단"""
        try:
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                await self.ffmpeg_process.wait()
                self.ffmpeg_process = None
            
            self.is_streaming = False
            logger.info(f"🛑 이벤트 {self.event_id} HLS 스트림 중단")
            
        except Exception as e:
            logger.error(f"이벤트 {self.event_id} HLS 스트림 중단 오류: {e}")
    
    async def start_background_music(self, event):
        """배경음악 시작 (자동 스케줄러에서 호출)"""
        try:
            event_id = event['event_id']
            message = event['message']
            
            await self.send(text_data=json.dumps({
                'type': 'start_background_music',
                'event_id': event_id,
                'message': message
            }))
            
            logger.info(f"🎵 이벤트 {event_id} 배경음악 시작: {message}")
            
        except Exception as e:
            logger.error(f"배경음악 시작 오류: {e}")
    
    # AI 중계멘트 관련 함수들은 ClubRadioConsumer에서 처리하므로 제거
    
    async def radio_stopped(self, event):
        """라디오 중단 처리"""
        try:
            event_id = event['event_id']
            message = event['message']
            
            await self.send(text_data=json.dumps({
                'type': 'radio_stopped',
                'event_id': event_id,
                'message': message
            }))
            
        except Exception as e:
            logger.error(f"라디오 중단 처리 오류: {e}")
    
    async def test_message(self, event):
        """테스트 메시지 처리"""
        try:
            message = event['message']
            logger.info(f"🧪 테스트 메시지 수신: {message}")
            
            await self.send(text_data=json.dumps({
                'type': 'test_response',
                'message': f'테스트 응답: {message}'
            }))
            
        except Exception as e:
            logger.error(f"테스트 메시지 처리 오류: {e}")

    @database_sync_to_async
    def _get_current_event(self, club_id):
        now = timezone.now()
        try:
            # 우선 진행 중 이벤트
            evt = Event.objects.filter(club_id=club_id, start_date_time__lte=now, end_date_time__gte=now).order_by('-start_date_time').first()
            if evt:
                return evt
            # 다음 예정 이벤트
            evt = Event.objects.filter(club_id=club_id, start_date_time__gte=now).order_by('start_date_time').first()
            return evt
        except Event.DoesNotExist:
            return None
"""