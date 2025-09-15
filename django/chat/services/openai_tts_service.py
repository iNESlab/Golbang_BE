import os
import logging
import asyncio
import aiohttp
import random
from django.conf import settings

logger = logging.getLogger(__name__)

class OpenAITTSService:
    """
    OpenAI TTS API를 사용한 텍스트-음성 변환 서비스
    - 실제 OpenAI TTS-1 모델 사용
    - API 키가 없거나 실패 시 더미 음성 사용
    """
    
    def __init__(self):
        # OpenAI API 키 확인
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY가 설정되지 않음. 더미 음성 사용")
        else:
            logger.info("🔑 OpenAI API 키 확인됨")
    
    async def generate_speech(self, text: str) -> bytes | None:
        """OpenAI TTS API를 사용해 텍스트를 음성으로 변환"""
        try:
            if not self.api_key:
                logger.info("🔇 API 키 없음 → 더미 음성 사용")
                return await self._use_dummy_speech()
            
            # OpenAI TTS API 호출
            logger.info("🎤 OpenAI TTS 요청: %s", text[:50] + "..." if len(text) > 50 else text)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "tts-1",  # tts-1 (빠름) 또는 tts-1-hd (고품질)
                "input": text,
                "voice": "alloy",  # alloy, echo, fable, onyx, nova, shimmer
                "response_format": "mp3",
                "speed": 1.25  # 1.25배속 (0.25 ~ 4.0 범위)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info("✅ OpenAI TTS 성공: %d bytes", len(audio_data))
                        return audio_data
                    else:
                        error_text = await response.text()
                        logger.error("❌ OpenAI TTS 실패 (%d): %s", response.status, error_text)
                        return await self._use_dummy_speech()
                        
        except asyncio.TimeoutError:
            logger.error("⏰ OpenAI TTS 타임아웃")
            return await self._use_dummy_speech()
        except Exception as e:
            logger.error("❌ OpenAI TTS 오류: %s", e)
            return await self._use_dummy_speech()
    
    async def _use_dummy_speech(self) -> bytes | None:
        """더미 음성 파일 사용 (fallback)"""
        try:
            audio_dir = os.path.join(settings.BASE_DIR, 'media', 'audio')
            if not os.path.exists(audio_dir):
                logger.error("media/audio 디렉토리가 없습니다")
                return None
                
            candidates = [f for f in os.listdir(audio_dir) if f.startswith("commentary_") and f.endswith(".mp3")]
            if not candidates:
                logger.error("commentary_*.mp3 파일이 없습니다")
                return None

            choice = random.choice(candidates)
            file_path = os.path.join(audio_dir, choice)
            logger.info("📢 더미 음성 사용: %s", choice)

            with open(file_path, "rb") as fp:
                return fp.read()
        except Exception as e:
            logger.error("더미 음성 오류: %s", e)
            return None
