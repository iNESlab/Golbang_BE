from django.apps import AppConfig
import asyncio
import logging
import threading

logger = logging.getLogger(__name__)

class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = '채팅 시스템'
    
    def ready(self):
        """앱이 준비되었을 때 호출되는 메서드"""
        try:
            import chat.signals  # 시그널 등록
            
            # 자동 라디오 스케줄러 시작
            from .auto_radio_scheduler import auto_radio_scheduler
            
            def run_scheduler():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(auto_radio_scheduler.start_monitoring())
            
            # 별도 스레드에서 스케줄러 실행
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            
            logger.info("🎵 자동 라디오 스케줄러 시작됨")
            
        except ImportError:
            pass
        except Exception as e:
            logger.error(f"❌ 자동 라디오 스케줄러 시작 실패: {e}")
        
