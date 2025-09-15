# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
import asyncio
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from events.models import Event
from channels.layers import get_channel_layer
import json

logger = logging.getLogger(__name__)

class AutoRadioScheduler:
    """
    🎵 자동 라디오 스케줄러 (클럽별 이벤트 관리)
    - 각 클럽별로 가장 최근 이벤트 기준으로 라디오 운영
    - 경기 30분 전 자동 시작
    - 경기 시작 시 오프닝멘트
    - 2분마다 중계멘트 생성
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
        self.running_events = {}  # {event_id: task}
        self.club_active_events = {}  # {club_id: event_id} - 각 클럽의 활성 이벤트
        
    async def start_monitoring(self):
        """모니터링 시작"""
        while True:
            try:
                await self._check_events()
                await asyncio.sleep(30)  # 30초마다 체크
            except Exception as e:
                logger.error(f"모니터링 오류: {e}")
                await asyncio.sleep(60)
    
    async def _check_events(self):
        """이벤트 체크 및 자동 시작 (클럽별 관리)"""
        try:
            now = timezone.now()
            
            # 모든 클럽의 이벤트들을 클럽별로 그룹화
            all_events = Event.objects.filter(
                start_date_time__lte=now + timedelta(minutes=30),
                start_date_time__gte=now - timedelta(hours=2),  # 2시간 전부터 체크
                status='SCHEDULED'
            ).order_by('club_id', '-start_date_time')
            
            # 클럽별로 가장 최근 이벤트 찾기
            club_latest_events = {}
            for event in all_events:
                if event.club_id not in club_latest_events:
                    club_latest_events[event.club_id] = event
            
            # 각 클럽의 최근 이벤트 처리
            for club_id, event in club_latest_events.items():
                # 이전 이벤트가 있으면 중단
                if club_id in self.club_active_events:
                    old_event_id = self.club_active_events[club_id]
                    if old_event_id != event.id:
                        await self._stop_club_radio(club_id, old_event_id)
                
                # 새 이벤트 시작 (30분 전부터)
                if event.start_date_time <= now + timedelta(minutes=30):
                    if event.id not in self.running_events:
                        await self._start_event_radio(event)
                        self.club_active_events[club_id] = event.id
            
            # 완료된 이벤트들 정리
            for event_id, task in list(self.running_events.items()):
                if task.done():
                    del self.running_events[event_id]
                    # 클럽별 활성 이벤트에서도 제거
                    for club_id, active_event_id in list(self.club_active_events.items()):
                        if active_event_id == event_id:
                            del self.club_active_events[club_id]
                            break
                    
        except Exception as e:
            logger.error(f"이벤트 체크 오류: {e}")
    
    async def _start_event_radio(self, event):
        """이벤트 라디오 시작"""
        try:
            # 라디오 시작 태스크 생성
            task = asyncio.create_task(self._run_event_radio(event))
            self.running_events[event.id] = task
            
            logger.info(f"🎵 클럽 {event.club_id} 이벤트 {event.id} 라디오 자동 시작")
            
        except Exception as e:
            logger.error(f"이벤트 라디오 시작 오류: {e}")
    
    async def _stop_club_radio(self, club_id, event_id):
        """클럽 라디오 중단"""
        try:
            if event_id in self.running_events:
                # 실행 중인 태스크 중단
                task = self.running_events[event_id]
                task.cancel()
                del self.running_events[event_id]
            
            # 클럽 그룹에 중단 메시지 전송
            await self.channel_layer.group_send(
                f'radio_club_{club_id}',
                {
                    'type': 'radio_stopped',
                    'club_id': club_id,
                    'event_id': event_id,
                    'message': f'클럽 {club_id} 라디오가 중단되었습니다'
                }
            )
            
            logger.info(f"🛑 클럽 {club_id} 이벤트 {event_id} 라디오 중단")
            
        except Exception as e:
            logger.error(f"클럽 라디오 중단 오류: {e}")
    
    async def _run_event_radio(self, event):
        """이벤트 라디오 실행"""
        try:
            # 30분 전부터 배경음악 시작
            await self._start_background_music(event)
            
            # 경기 시작까지 대기
            await self._wait_for_event_start(event)
            
            # 오프닝멘트 재생
            await self._play_opening_commentary(event)
            
            # 2분마다 중계멘트 생성
            await self._run_commentary_loop(event)
            
        except Exception as e:
            logger.error(f"이벤트 라디오 실행 오류: {e}")
        finally:
            # 완료 후 정리
            if event.id in self.running_events:
                del self.running_events[event.id]
    
    async def _start_background_music(self, event):
        """배경음악 시작"""
        try:
            # 클럽별 라디오 그룹에 배경음악 시작 메시지 전송
            await self.channel_layer.group_send(
                f'radio_club_{event.club_id}',
                {
                    'type': 'start_background_music',
                    'club_id': event.club_id,
                    'event_id': event.id,
                    'message': f'클럽 {event.club_id} 배경음악을 시작합니다'
                }
            )
            
            logger.info(f"🎵 클럽 {event.club_id} 이벤트 {event.id} 배경음악 시작")
            
        except Exception as e:
            logger.error(f"배경음악 시작 오류: {e}")
    
    async def _wait_for_event_start(self, event):
        """경기 시작까지 대기"""
        try:
            now = timezone.now()
            start_time = event.start_date_time
            
            if start_time > now:
                wait_seconds = (start_time - now).total_seconds()
                logger.info(f"⏰ 이벤트 {event.id} 시작까지 {wait_seconds:.0f}초 대기")
                await asyncio.sleep(wait_seconds)
            
        except Exception as e:
            logger.error(f"경기 시작 대기 오류: {e}")
    
    async def _play_opening_commentary(self, event):
        """오프닝멘트 재생"""
        try:
            # AI 오프닝멘트 생성 (실제로는 AI 서비스 호출)
            opening_text = f"안녕하세요! 클럽 {event.club_id}의 {event.event_title} 골프 이벤트가 시작됩니다!"
            
            # 오프닝멘트를 클럽 그룹에 전송
            await self.channel_layer.group_send(
                f'radio_club_{event.club_id}',
                {
                    'type': 'play_commentary',
                    'club_id': event.club_id,
                    'event_id': event.id,
                    'text': opening_text,
                    'commentary_type': 'opening'
                }
            )
            
            logger.info(f"🎤 클럽 {event.club_id} 이벤트 {event.id} 오프닝멘트 재생")
            
        except Exception as e:
            logger.error(f"오프닝멘트 재생 오류: {e}")
    
    async def _run_commentary_loop(self, event):
        """중계멘트 루프 실행"""
        try:
            commentary_count = 0
            
            while True:
                # 2분 대기
                await asyncio.sleep(120)
                
                # 이벤트가 끝났는지 체크
                if timezone.now() > event.end_date_time:
                    break
                
                # 중계멘트 생성
                commentary_count += 1
                commentary_text = f"현재 {event.event_title} 경기가 진행 중입니다. {commentary_count}번째 중계멘트입니다."
                
                # 중계멘트를 클럽 그룹에 전송
                await self.channel_layer.group_send(
                    f'radio_club_{event.club_id}',
                    {
                        'type': 'play_commentary',
                        'club_id': event.club_id,
                        'event_id': event.id,
                        'text': commentary_text,
                        'commentary_type': 'regular',
                        'commentary_count': commentary_count
                    }
                )
                
                logger.info(f"🎤 이벤트 {event.id} 중계멘트 {commentary_count} 재생")
                
        except Exception as e:
            logger.error(f"중계멘트 루프 오류: {e}")

# 전역 스케줄러 인스턴스
auto_radio_scheduler = AutoRadioScheduler()
"""
