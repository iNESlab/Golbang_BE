# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
RTMP 기반 방송 서비스
nginx-rtmp 미디어 서버를 사용하여 안정적인 라이브 스트리밍을 제공합니다.
"""
"""
from datetime import timedelta
import asyncio
import logging
import os
from django.utils import timezone
from django.conf import settings
from channels.db import database_sync_to_async

from events.models import Event
from participants.models import HoleScore
from chat.models import ChatMessage, ChatRoom
from .ai_commentary_service import AICommentaryService
from .openai_tts_service import OpenAITTSService
from .rtmp_service import rtmp_service

logger = logging.getLogger(__name__)

class RTMPBroadcastService:
    \"\"\"
    RTMP 기반 클럽별 라디오 방송 서비스
    • nginx-rtmp 미디어 서버 사용으로 안정성 향상
    • 클럽별 독립적인 스트림 관리
    • Safari 호환성 및 404 에러 방지
    \"\"\"

    def __init__(self):
        self.active_clubs: dict[int, dict] = {}  # club_id -> broadcast_info
        self.last_commentary_times: dict[int, timezone.datetime] = {}
        self.ai_service = AICommentaryService()
        self.tts_service = OpenAITTSService()

    async def start_club_broadcast(self, club_id: int) -> bool:
        \"\"\"클럽 방송을 시작한다.\"\"\"
        try:
            logger.info(f"🎯 클럽 {club_id} 방송 시작 시도...")
            
            # 현재 진행중인 이벤트 확인
            event = await self._get_active_event_for_club(club_id)
            if not event:
                logger.warning(f"❌ 클럽 {club_id}에 진행 중인 이벤트가 없습니다")
                return False

            logger.info(f"✅ 클럽 {club_id} 활성 이벤트 찾음: {event.id} - {event.event_title}")

            # 방송 시간 범위 확인
            if not self._is_within_broadcast_window(event):
                logger.warning(f"❌ 이벤트 {event.id}가 방송 시간 범위에 없습니다")
                logger.info(f"📅 이벤트 시간: {event.start_date_time} ~ {event.end_date_time}")
                logger.info(f"🕐 현재 시간: {timezone.now()}")
                return False

            logger.info(f"✅ 클럽 {club_id} 방송 시간 조건 만족")

            # 이미 방송 중인지 확인
            if club_id in self.active_clubs:
                logger.info(f"✅ 클럽 {club_id} 방송이 이미 실행 중입니다")
                return True

            # 🔥 강제 방송 시작: 이벤트가 있으면 무조건 방송 켜기
            logger.info(f"🚀 이벤트가 있으므로 클럽 {club_id} 방송을 강제 시작합니다")
            
            # 배경음악 스트림 시작
            stream_key = f"club_{club_id}"
            audio_file = os.path.join(settings.MEDIA_ROOT, 'audio', 'background_default.mp3')
            logger.info(f"🎵 클럽 {club_id} 배경음악 스트림 시작 시도: {stream_key}")
            
            success = await rtmp_service.start_background_stream(stream_key, audio_file)
            if not success:
                logger.error(f"❌ 클럽 {club_id} 배경음악 스트림 시작 실패 - 재시도 중...")
                # 재시도 로직 추가
                await asyncio.sleep(2)
                success = await rtmp_service.start_background_stream(stream_key, audio_file)
                if not success:
                    logger.error(f"❌ 클럽 {club_id} 배경음악 스트림 재시도도 실패")
                    return False

            logger.info(f"✅ 클럽 {club_id} 배경음악 스트림 시작 성공")

            # 방송 정보 저장
            self.active_clubs[club_id] = {
                'event_id': event.id,
                'stream_key': stream_key,
                'started_at': timezone.now(),
                'opening_played': False
            }

            # 방송 루프 시작
            broadcast_task = asyncio.create_task(self._broadcast_loop(club_id, event))
            self.active_clubs[club_id]['task'] = broadcast_task

            logger.info(f"✅ 클럽 {club_id} RTMP 방송 시작 완료 (이벤트 {event.id})")
            return True

        except Exception as e:
            logger.error(f"❌ 클럽 {club_id} 방송 시작 실패: {e}")
            import traceback
            logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
            return False

    async def stop_club_broadcast(self, club_id: int) -> bool:
        \"\"\"클럽 방송을 중지한다.\"\"\"
        try:
            if club_id not in self.active_clubs:
                logger.info(f"클럽 {club_id} 방송이 실행 중이지 않습니다")
                return True

            broadcast_info = self.active_clubs[club_id]
            
            # 방송 태스크 중지
            if 'task' in broadcast_info:
                broadcast_info['task'].cancel()
                try:
                    await broadcast_info['task']
                except asyncio.CancelledError:
                    pass

            # RTMP 스트림 중지
            stream_key = broadcast_info['stream_key']
            await rtmp_service._stop_stream(stream_key)

            # 방송 정보 제거
            del self.active_clubs[club_id]
            
            # 해설 시간 정보도 정리
            if club_id in self.last_commentary_times:
                del self.last_commentary_times[club_id]

            logger.info(f"🛑 클럽 {club_id} RTMP 방송 중지")
            return True

        except Exception as e:
            logger.error(f"❌ 클럽 {club_id} 방송 중지 실패: {e}")
            return False

    async def _broadcast_loop(self, club_id: int, event: Event):
        \"\"\"방송 메인 루프\"\"\"
        try:
            logger.info(f"🔄 클럽 {club_id} 방송 루프 시작 (이벤트 {event.id})")
            logger.info(f"🎯 DEBUG: 방송 루프 진입됨 - 클럽 {club_id}, 이벤트 {event.id}")
            
            # 이벤트 시작 시간까지 대기 후 오프닝 해설 생성
            if not self.active_clubs[club_id]['opening_played']:
                now = timezone.now()
                if now < event.start_date_time:
                    wait_seconds = (event.start_date_time - now).total_seconds()
                    logger.info(f"⌛ 이벤트 시작까지 {wait_seconds:.1f}초 대기 (클럽 {club_id})")
                    await asyncio.sleep(wait_seconds)
                    
                    # 이벤트 시작 시간이 되었을 때만 오프닝 해설 생성
                    current_time = timezone.now()
                    if current_time >= event.start_date_time and current_time <= event.start_date_time + timedelta(minutes=5):
                        logger.info(f"🎤 이벤트 시작! 오프닝 해설 생성 (클럽 {club_id})")
                        await self._generate_opening_commentary(club_id, event)
                        self.active_clubs[club_id]['opening_played'] = True
                        logger.info(f"✅ 오프닝 해설 완료, 주기적 루프로 진행 (클럽 {club_id})")
                    else:
                        logger.info(f"⏰ 오프닝 해설 시간이 아님 (현재: {current_time}, 시작: {event.start_date_time})")
                        self.active_clubs[club_id]['opening_played'] = True  # 이미 지났으므로 스킵
                else:
                    # 이미 이벤트 시작 시간이 지났으면 오프닝 해설 스킵
                    logger.info(f"⏰ 이벤트 시작 시간이 이미 지났습니다. 오프닝 해설 스킵 (클럽 {club_id})")
                    self.active_clubs[club_id]['opening_played'] = True

            # 주기적 해설 루프
            commentary_count = 1
            logger.info(f"🔄 주기적 해설 루프 시작 - 클럽 {club_id}")
            while club_id in self.active_clubs:
                logger.info(f"🔄 루프 진입 - 클럽 {club_id}, 체크 #{commentary_count}")
                try:
                    # 테스트를 위해 30초로 변경
                    await asyncio.sleep(30)  # 30초마다 체크
                    
                    # 이벤트가 아직 진행 중인지 확인
                    if not self._is_within_broadcast_window(event):
                        logger.info(f"이벤트 {event.id} 방송 시간 종료")
                        break
                    
                    # 활동 확인 (30초마다 체크, 2분간 활동이 있으면 해설 생성)
                    logger.info(f"🔍 활동 확인 중... (클럽 {club_id}, 체크 #{commentary_count})")
                    
                    if await self._check_recent_activity(event, club_id):
                        # 마지막 해설 시간 체크 (중복 방지)
                        last_commentary_time = self.last_commentary_times.get(club_id)
                        if last_commentary_time:
                            time_since_last = (timezone.now() - last_commentary_time).total_seconds()
                            if time_since_last < 120:  # 2분 미만이면 스킵
                                logger.info(f"⏰ 마지막 해설 후 {time_since_last:.1f}초 경과. 2분 대기 중... (클럽 {club_id})")
                                continue
                        
                        logger.info(f"🎯 활동 감지! 해설 생성 시작 (클럽 {club_id})")
                        await self._generate_periodic_commentary(club_id, event, commentary_count)
                        commentary_count += 1
                    else:
                        logger.info(f"✅ 최근 2분간 활동 없음 (이벤트 {event.id}). 해설 생략.")

                except asyncio.CancelledError:
                    logger.info(f"방송 루프 취소됨: 클럽 {club_id}")
                    break
                except Exception as e:
                    logger.error(f"❌ 방송 루프 오류 (클럽 {club_id}): {e}")
                    await asyncio.sleep(10)  # 오류 시 잠시 대기

        except asyncio.CancelledError:
            logger.info(f"방송 루프 취소됨: 클럽 {club_id}")
        except Exception as e:
            logger.error(f"❌ 방송 루프 치명적 오류 (클럽 {club_id}): {e}")
        finally:
            # 정리
            await self.stop_club_broadcast(club_id)


    async def _generate_opening_commentary(self, club_id: int, event: Event):
        \"\"\"오프닝 해설 생성 및 삽입\"\"\"
        try:
            logger.info(f"🎤 오프닝 해설 생성 시작 (클럽 {club_id})")
            
            # AI 해설 생성
            commentary_text = await self.ai_service.generate_opening_commentary(event, club_id)
            if not commentary_text:
                logger.error("오프닝 해설 텍스트 생성 실패")
                return

            # TTS 변환
            audio_data = await self.tts_service.generate_speech(commentary_text)
            if not audio_data:
                logger.error("오프닝 해설 TTS 변환 실패")
                return

            # RTMP 스트림에 해설 삽입
            stream_key = f"club_{club_id}"
            duration = len(audio_data) / 16000  # 대략적인 길이 추정
            
            # 클라이언트에게 해설 스트림 시작 알림
            await self._notify_stream_change(club_id, f"{stream_key}_commentary", "commentary_start")
            
            success = await rtmp_service.insert_commentary(stream_key, audio_data, duration)
            
            # 클라이언트에게 배경음악 스트림 복원 알림
            await self._notify_stream_change(club_id, stream_key, "commentary_end")
            
            if success:
                logger.info(f"✅ 오프닝 해설 삽입 완료 (클럽 {club_id})")
            else:
                logger.error(f"❌ 오프닝 해설 삽입 실패 (클럽 {club_id})")
                
            logger.info(f"🔚 오프닝 해설 함수 완료 (클럽 {club_id})")

        except Exception as e:
            logger.error(f"❌ 오프닝 해설 생성 오류 (클럽 {club_id}): {e}")
            logger.info(f"🔚 오프닝 해설 함수 예외 완료 (클럽 {club_id})")

    async def _generate_periodic_commentary(self, club_id: int, event: Event, count: int):
        \"\"\"주기적 해설 생성 및 삽입\"\"\"
        try:
            logger.info(f"🎤 주기적 해설 #{count} 생성 시작 (클럽 {club_id})")
            
            # AI 해설 생성
            commentary_text = await self.ai_service.generate_event_commentary(event, club_id)
            if not commentary_text:
                logger.warning(f"주기적 해설 #{count} 텍스트 생성 실패")
                return

            # TTS 변환
            audio_data = await self.tts_service.generate_speech(commentary_text)
            if not audio_data:
                logger.error(f"주기적 해설 #{count} TTS 변환 실패")
                return

            # RTMP 스트림에 해설 삽입
            stream_key = f"club_{club_id}"
            duration = len(audio_data) / 16000  # 대략적인 길이 추정
            
            # 클라이언트에게 해설 스트림 시작 알림
            await self._notify_stream_change(club_id, f"{stream_key}_commentary", "commentary_start")
            
            success = await rtmp_service.insert_commentary(stream_key, audio_data, duration)
            
            # 클라이언트에게 배경음악 스트림 복원 알림
            await self._notify_stream_change(club_id, stream_key, "commentary_end")
            if success:
                self.last_commentary_times[club_id] = timezone.now()
                logger.info(f"✅ 주기적 해설 #{count} 삽입 완료 (클럽 {club_id})")
            else:
                logger.error(f"❌ 주기적 해설 #{count} 삽입 실패 (클럽 {club_id})")

        except Exception as e:
            logger.error(f"❌ 주기적 해설 #{count} 생성 오류 (클럽 {club_id}): {e}")

    async def _check_recent_activity(self, event: Event, club_id: int) -> bool:
        \"\"\"최근 2분간 활동 확인\"\"\"
        try:
            two_minutes_ago = timezone.now() - timedelta(minutes=2)
            
            # 최근 점수 입력 확인
            recent_scores = await database_sync_to_async(
                lambda: HoleScore.objects.filter(
                    participant__event=event,
                    created_at__gte=two_minutes_ago
                ).exists()
            )()
            
            # 최근 채팅 확인 (클럽 채팅방에서)
            chat_room = await database_sync_to_async(
                lambda: ChatRoom.objects.filter(club_id=club_id, chat_room_type='CLUB').first()
            )()
            
            logger.info(f"🔍 채팅방 조회: 클럽 {club_id}, 채팅방: {chat_room}")
            
            recent_chats = False
            if chat_room:
                recent_chats = await database_sync_to_async(
                    lambda: ChatMessage.objects.filter(
                        chat_room=chat_room,
                        created_at__gte=two_minutes_ago
                    ).exists()
                )()
                logger.info(f"🔍 최근 채팅 확인: {recent_chats} (2분 전: {two_minutes_ago})")
            else:
                logger.warning(f"❌ 클럽 {club_id}의 채팅방을 찾을 수 없습니다")
            
            has_activity = recent_scores or recent_chats
            
            if has_activity:
                logger.info(f"🎯 최근 활동 감지됨 (이벤트 {event.id}): 점수={recent_scores}, 채팅={recent_chats}")
            
            return has_activity
            
        except Exception as e:
            logger.error(f"❌ 활동 확인 오류 (이벤트 {event.id}): {e}")
            return False

    async def _notify_stream_change(self, club_id: int, stream_key: str, action: str):
        \"\"\"클라이언트에게 스트림 변경 알림\"\"\"
        try:
            from channels.layers import get_channel_layer
            
            channel_layer = get_channel_layer()
            if not channel_layer:
                logger.warning("Channel layer가 없습니다")
                return
                
            # HLS URL 생성
            hls_url = f"http://localhost/hls/{stream_key}/index.m3u8"
            
            message = {
                'type': 'stream_change',
                'stream_key': stream_key,
                'hls_url': hls_url,
                'action': action,  # 'commentary_start' 또는 'commentary_end'
                'timestamp': timezone.now().isoformat()
            }
            
            # 클럽의 모든 라디오 클라이언트에게 전송
            group_name = f"rtmp_radio_club_{club_id}"
            await channel_layer.group_send(group_name, {
                'type': 'send_message',
                'message': message
            })
            
            logger.info(f"📡 스트림 변경 알림 전송: {action} -> {stream_key}")
            
        except Exception as e:
            logger.error(f"❌ 스트림 변경 알림 실패: {e}")

    async def _get_active_event_for_club(self, club_id: int) -> Event:
        \"\"\"클럽의 현재 진행중인 이벤트 조회\"\"\"
        try:
            now = timezone.now()
            event = await database_sync_to_async(
                lambda: Event.objects.filter(
                    club_id=club_id,
                    start_date_time__lte=now + timedelta(minutes=30),  # 30분 전부터
                    end_date_time__gte=now  # 아직 끝나지 않음
                ).order_by('-start_date_time').first()
            )()
            
            return event
        except Exception as e:
            logger.error(f"❌ 클럽 {club_id} 활성 이벤트 조회 오류: {e}")
            return None

    def _is_within_broadcast_window(self, event: Event) -> bool:
        \"\"\"방송 가능 시간인지 확인 (시작 24시간 전 ~ 종료 1시간 후)\"\"\"
        now = timezone.now()
        broadcast_start = event.start_date_time - timedelta(hours=24)
        broadcast_end = event.end_date_time + timedelta(hours=1)

        return broadcast_start <= now <= broadcast_end

    def get_hls_url(self, club_id: int) -> str:
        \"\"\"클럽의 HLS 스트림 URL 반환\"\"\"
        stream_key = f"club_{club_id}"
        return rtmp_service.get_hls_url(stream_key)

    def is_club_broadcasting(self, club_id: int) -> bool:
        \"\"\"클럽이 방송 중인지 확인\"\"\"
        return club_id in self.active_clubs

    async def get_broadcast_status(self, club_id: int) -> dict:
        \"\"\"클럽 방송 상태 조회\"\"\"
        if club_id not in self.active_clubs:
            return {'active': False}
        
        broadcast_info = self.active_clubs[club_id]
        stream_status = await rtmp_service.get_stream_status(broadcast_info['stream_key'])
        
        return {
            'active': True,
            'event_id': broadcast_info['event_id'],
            'started_at': broadcast_info['started_at'].isoformat(),  # JSON 직렬화 가능하도록 변환
            'opening_played': broadcast_info['opening_played'],
            'stream_status': stream_status,
            'hls_url': self.get_hls_url(club_id)
        }

# 싱글톤 인스턴스
rtmp_broadcast_service = RTMPBroadcastService()
"""