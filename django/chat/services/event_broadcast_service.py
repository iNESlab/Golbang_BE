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
# TODO: import actual hls_service once created

logger = logging.getLogger(__name__)

class EventBroadcastService:
    """
    이벤트 단위 라디오 방송 서비스.
    • 이벤트 시작 30분 전부터 종료 시까지만 방송 허용.
    • 오프닝 멘트 후 2분 주기로 AI 멘트 생성 → 배경 음악 일시정지 → 멘트 삽입 → 재개.
    • FFmpeg 중복 실행을 방지하기 위해 async lock 사용.
    """

    def __init__(self):
        self.active_events: dict[int, asyncio.Task] = {}
        self.last_broadcast_time: dict[int, timezone.datetime] = {}
        self.last_commentary_times: dict[int, timezone.datetime] = {}  # 마지막 해설 생성 시간 추적
        self.ffmpeg_lock = asyncio.Lock()
        self.ai_service = AICommentaryService()
        self.tts_service = OpenAITTSService()

    async def start_event_broadcast(self, event_id: int) -> bool:
        """이벤트 방송을 시작한다. 이미 실행 중이면 True 반환."""
        if event_id in self.active_events:
            logger.info("event %s broadcast already running", event_id)
            return True

        event = await self._get_event(event_id)
        if not event:
            logger.warning("event %s not found", event_id)
            return False

        if not self._is_within_broadcast_window(event):
            logger.warning("event %s not in broadcast window", event_id)
            return False

        # 배경음악 스트림 시작 (오프닝은 게임 시작 시각에) - club 기반
        from .hls_service import hls_service
        club_id = event.club_id  # event에서 club_id 가져오기
        await hls_service.start_stream(club_id, "/app/media/audio/background_default.mp3")

        task = asyncio.create_task(self._broadcast_loop(event_id))
        self.active_events[event_id] = task
        logger.info("event %s broadcast task started", event_id)
        return True

    async def stop_event_broadcast(self, event_id: int):
        task = self.active_events.pop(event_id, None)
        if task:
            task.cancel()
        self.last_broadcast_time.pop(event_id, None)
        from .hls_service import hls_service
        event = await self._get_event(event_id)
        if event:
            club_id = event.club_id
            await hls_service.stop_stream(club_id)
        logger.info("event %s broadcast stopped", event_id)

    async def _broadcast_loop(self, event_id: int):
        try:
            event = await self._get_event(event_id)

            logger.info("📡 broadcast loop START event=%s now=%s start=%s", event_id, timezone.now(), event.start_date_time)

            # 게임 시작 시각까지 대기
            now = timezone.now()
            if now < event.start_date_time:
                logger.info("⌛ waiting %s seconds for game start", (event.start_date_time - now).total_seconds())
                wait_seconds = (event.start_date_time - now).total_seconds()
                logger.info("event %s waiting %d seconds for game start", event_id, wait_seconds)
                await asyncio.sleep(wait_seconds)

                # 오프닝 멘트 생성
                logger.info("🎬 GENERATE OPENING for event %s", event_id)
                await self._generate_opening(event)
                # 오프닝은 last_commentary_times 에 기록하지 않는다.

            # 3. 30초마다 활동 체크, 2분 간격으로 해설 생성
            loop_count = 0
            check_count = 0
            while True:
                check_count += 1
                logger.info("🔍 Activity Check #%d: Checking for new activity... (event %s)", check_count, event_id)
                await asyncio.sleep(30) # 30초마다 체크
                
                # 방송 시간이 종료되었는지 확인
                event = await self._get_event(event_id)
                if timezone.localtime() > timezone.localtime(event.end_date_time):
                    logger.info("🔚 Event %s has ended. Stopping broadcast loop.", event_id)
                    break

                # --- 마지막 해설 이후 새로운 활동(스코어, 채팅)이 있었는지 확인 ---
                has_new_activity = await self._check_for_new_activity_since_last_commentary(event_id)
                
                # 2분이 지났는지 확인 (마지막 해설로부터)
                last_commentary_time = self.last_commentary_times.get(event_id)
                time_since_last_commentary = 0
                if last_commentary_time:
                    time_since_last_commentary = (timezone.now() - last_commentary_time).total_seconds()
                    
                logger.info("📊 Activity Status (event %s): New Activity = %s, Time since last commentary = %.1fs", 
                          event_id, has_new_activity, time_since_last_commentary)
                
                if not has_new_activity:
                    logger.info("⭕ No new activity since last commentary for event %s. Waiting...", event_id)
                    continue

                # 해설 생성 조건
                should_generate = False
                if last_commentary_time is None:
                    # 아직 중간 해설이 한 번도 없었으면 즉시 생성
                    should_generate = True
                elif time_since_last_commentary >= 120:
                    should_generate = True

                if not should_generate:
                    logger.info("⏰ New activity found, but only %.1fs passed since last commentary. Waiting for 2min interval...", 
                              time_since_last_commentary)
                    continue
                # ---------------------------------------------------------

                loop_count += 1
                logger.info("🎙️ GENERATE COMMENTARY #%d for event %s (new activity + 2min passed)", loop_count, event_id)
                await self._generate_commentary(event_id)
                # 해설 생성 시간 기록
                self.last_commentary_times[event_id] = timezone.now()
        except asyncio.CancelledError:
            logger.info("event %s broadcast loop cancelled", event_id)
        except Exception as e:
            logger.error("commentary gen error: %s", e, exc_info=True)
        finally:
            await self.stop_event_broadcast(event_id)
            # 정리 작업
            if event_id in self.last_commentary_times:
                del self.last_commentary_times[event_id]

    def _should_broadcast(self, event_id: int) -> bool:
        last = self.last_broadcast_time.get(event_id)
        if last is None:
            return True
        return timezone.now() - last >= timedelta(minutes=2)

    async def _generate_opening(self, event):
        try:
            logger.info("📝 _generate_opening start for %s", event.id)
            
            logger.info("  -> Calling AI service for opening text...")
            text = await self.ai_service.generate_opening_commentary(event)
            if not text:
                logger.warning("  -> AI service returned no opening text. Skipping.")
                return

            logger.info("  -> AI service returned opening text: '%s...'", text[:30])
            logger.info("  -> Calling TTS service for opening audio...")
            audio = await self.tts_service.generate_speech(text)
            if not audio:
                logger.warning("  -> TTS service returned no opening audio. Skipping.")
                return

            logger.info("  -> TTS service returned opening audio (%d bytes). Adding to HLS stream.", len(audio))
            from .hls_service import hls_service
            await hls_service.add_commentary_segment(event.club_id, audio)
            
            logger.info("opening commentary added for event %s", event.id)
            self.last_broadcast_time[event.id] = timezone.now()
        except Exception as e:
            logger.error("opening commentary error: %s", e, exc_info=True)

    async def _generate_commentary(self, event_id: int):
        try:
            logger.info("📝 _generate_commentary start for %s", event_id)
            event = await self._get_event(event_id)
            
            logger.info("  -> Calling AI service to generate text...")
            text = await self.ai_service.generate_event_commentary(event)
            if not text:
                logger.warning("  -> AI service returned no text. Skipping commentary.")
                return

            logger.info("  -> AI service returned text: '%s...'", text[:30])
            logger.info("  -> Calling TTS service to generate audio...")
            audio = await self.tts_service.generate_speech(text)
            if not audio:
                logger.warning("  -> TTS service returned no audio. Skipping commentary.")
                return

            logger.info("  -> TTS service returned audio (%d bytes). Adding to HLS stream.", len(audio))
            from .hls_service import hls_service
            await hls_service.add_commentary_segment(event.club_id, audio)
            
            logger.info("periodic commentary added for event %s", event_id)
            self.last_broadcast_time[event_id] = timezone.now()
        except Exception as e:
            logger.error("commentary gen error: %s", e, exc_info=True)

    async def _get_event(self, event_id):
        from asgiref.sync import sync_to_async
        return await sync_to_async(Event.objects.select_related('club').get)(id=event_id)

    async def _check_for_new_activity_since_last_commentary(self, event_id: int) -> bool:
        """마지막 해설 생성 이후 새로운 활동(점수, 채팅) 확인"""
        # 마지막 해설 생성 시간을 기준으로 활동 확인
        last_commentary_time = self.last_commentary_times.get(event_id)
        if last_commentary_time:
            since_datetime = last_commentary_time
            logger.info("🔍 Activity check for event %d since last commentary: %s", event_id, since_datetime)
        else:
            # 첫 번째 해설이면 방송 시작 시간부터 확인 - 더 넓은 범위로 확인
            event = await self._get_event(event_id)
            since_datetime = event.start_date_time  # 이벤트 시작 시간부터 모든 활동 확인
            logger.info("🔍 First activity check for event %d since EVENT START: %s", event_id, since_datetime)
            # 첫 번째 체크에서는 시간을 기록하지 않음 - 실제 해설 생성 후에 기록
            
        return await self._check_activity_since_time(event_id, since_datetime)
    
    @staticmethod
    @database_sync_to_async
    def _check_activity_since_time(event_id: int, since_datetime) -> bool:
        """특정 시간 이후의 새로운 스코어 입력이나 채팅 메시지가 있었는지 확인"""
        logger.info("🔍 Checking activity for event %d since %s", event_id, since_datetime)

        # 1. 새로운 스코어 확인
        scores_query = HoleScore.objects.filter(
            participant__event_id=event_id,
            created_at__gte=since_datetime
        )
        new_scores_exist = scores_query.exists()
        scores_count = scores_query.count()
        
        logger.info("📊 Scores query: found %d scores since %s", scores_count, since_datetime)

        if new_scores_exist:
            logger.info("📈 New score detected for event %d", event_id)
            return True

        # 2. 새로운 채팅 메시지 확인 (이벤트와 연관된 클럽의 채팅방 확인)
        try:
            # 먼저 이벤트 정보를 가져와서 club_id 확인
            from events.models import Event
            event = Event.objects.get(id=event_id)
            club_id = event.club_id
            
            # 클럽 채팅방에서 메시지 확인 (실제로는 클럽 기반으로 채팅방이 생성됨)
            chat_room = ChatRoom.objects.get(club_id=club_id, chat_room_type='CLUB')
            messages_query = ChatMessage.objects.filter(
                chat_room=chat_room,
                created_at__gte=since_datetime
            ).exclude(message_type='SYSTEM')
            new_messages_exist = messages_query.exists()
            messages_count = messages_query.count()
            
            logger.info("💬 Messages query (club %d): found %d messages since %s", club_id, messages_count, since_datetime)

            if new_messages_exist:
                logger.info("💬 New chat message detected for event %d (club %d)", event_id, club_id)
                return True
        except (ChatRoom.DoesNotExist, Event.DoesNotExist):
            logger.warning("⚠️ No CLUB chat room found for event %d", event_id)
            pass

        logger.info("❌ No new activity found for event %d", event_id)
        return False
        
    def _is_within_broadcast_window(self, event) -> bool:
        """시작 30분 전~종료까지 (로컬 타임존 기준)"""
        now = timezone.localtime()
        start = timezone.localtime(event.start_date_time)
        end = timezone.localtime(event.end_date_time)
        logger.info("🕒 window check | start-30=%s | start=%s | end=%s | now=%s",
                    start - timedelta(minutes=30), start, end, now)
        return start - timedelta(minutes=30) <= now <= end

# singleton
event_broadcast_service = EventBroadcastService()
