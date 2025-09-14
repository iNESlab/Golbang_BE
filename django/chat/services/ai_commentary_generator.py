import asyncio
import logging
import base64
import openai
from django.conf import settings
from events.models import Event

logger = logging.getLogger(__name__)

class AICommentaryGenerator:
    """
    🎤 AI 중계멘트 생성기
    - 오프닝멘트 생성
    - 2분마다 중계멘트 생성
    - TTS로 오디오 변환
    """
    
    def __init__(self):
        self.openai_client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY
        )
    
    def _make_opening_prompt(self, event: Event) -> str:
        """Opening prompt string (sync helper)"""
        return f"""
당신은 전문 골프 중계방송 캐스터입니다. 골프 토너먼트의 오프닝 중계방송을 작성해주세요.

골프장: {event.location or '미정'}
날짜: {event.start_date_time.strftime('%Y년 %m월 %d일')}
이벤트: {event.event_title}

다음 형식으로 작성해주세요:
캐스터 박진우: [오프닝 멘트]
김프로: [해설가 멘트]

실제 골프 방송처럼 생생하고 임팩트 있게 작성해주세요. 날씨와 골프장 분위기를 포함해서 작성해주세요.
"""

    def _make_commentary_prompt(self, event: Event, commentary_count: int) -> str:
        return f"""
당신은 프로 골프 중계방송 캐스터입니다. 지난 1분간의 주요 점수 변화를 자연스럽게 중계해주세요.

※ 반드시 실제 입력된 점수 정보만 바탕으로 해설하세요.
※ 샷의 구체적 상황이나 현장에서 볼 수 있는 정보는 언급하지 마세요.
※ 입력 데이터에 없는 내용은 상상해서 넣지 마세요.
※ 채팅을 전부 다 읽어줄 필요는 없습니다. 재밌거나 임팩트 있는 것만 몇 개 골라서 자연스럽게 언급하세요. 다만 없는 채팅을 지어내지 마세요.
※ 생성되는 전체 중계방송 스크립트는 실제 사람이 읽었을 때 1분을 넘기면 안 됩니다. 너무 길게 작성하지 말고, 1분 이내에 읽을 수 있을 정도의 분량(최대 600~800자, 200~300단어)로 작성하세요.

이벤트 정보:
- 제목: {event.event_title}
- 장소: {event.location or '미정'}
- 중계멘트 순서: {commentary_count}번째

점수 중계를 하면서 시청자들의 반응도 적절히 언급해주세요. 
예를 들어: 
- "선수의 멋진 플레이에 시청자분들도 환호하고 계시네요"
- "시청자분들도 이번 홀의 난이도를 체감하고 계시는 것 같습니다"
- "시청자분들의 반응이 뜨거우시네요!"

전문적이면서도 친근하고 재미있게 중계해주세요. 너무 딱딱하지 않게, 적절한 유머도 섞어주세요.
"""

    async def generate_opening_commentary(self, event: Event) -> tuple[str, bytes]:
        """오프닝멘트 생성"""
        try:
            prompt = self._make_opening_prompt(event)
            logger.info("🖋️ OPENING PROMPT:\n%s", prompt)
            # 오프닝멘트 텍스트 생성
            opening_text = await self._generate_opening_text(event)
            logger.info("📝 OPENING TEXT GENERATED:\n%s", opening_text)
            
            # TTS로 오디오 생성
            audio_data = await self._text_to_speech(opening_text)
            
            logger.info(f"🎤 오프닝멘트 생성 완료: {event.id}")
            return opening_text, audio_data
            
        except Exception as e:
            logger.error(f"오프닝멘트 생성 오류: {e}")
            return "", b""
    
    async def generate_regular_commentary(self, event: Event, commentary_count: int) -> tuple[str, bytes]:
        """정기 중계멘트 생성"""
        try:
            prompt = self._make_commentary_prompt(event, commentary_count)
            logger.info("🖋️ COMMENTARY PROMPT #%d:\n%s", commentary_count, prompt)
            # 중계멘트 텍스트 생성
            commentary_text = await self._generate_commentary_text(event, commentary_count)
            logger.info("📝 COMMENTARY TEXT #%d GENERATED:\n%s", commentary_count, commentary_text)
            
            # TTS로 오디오 생성
            audio_data = await self._text_to_speech(commentary_text)
            
            logger.info(f"🎤 중계멘트 {commentary_count} 생성 완료: {event.id}")
            return commentary_text, audio_data
            
        except Exception as e:
            logger.error(f"중계멘트 생성 오류: {e}")
            return "", b""
    
    async def _generate_opening_text(self, event: Event) -> str:
        """오프닝멘트 텍스트 생성"""
        try:
            prompt = f"""
            골프 이벤트 오프닝멘트를 작성해주세요.
            
            이벤트 정보:
            - 제목: {event.event_title}
            - 장소: {event.location or '미정'}
            - 시작시간: {event.start_date_time.strftime('%Y년 %m월 %d일 %H시 %M분')}
            
            요구사항:
            - 30초 내외의 길이
            - 골프 전문 캐스터 톤
            - 이벤트에 대한 기대감 조성
            - 자연스럽고 생동감 있는 표현
            - 같은 문장을 두 번 이상 반복하지 마세요
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 골프 전문 캐스터입니다. 생동감 있고 전문적인 중계멘트를 작성해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"오프닝멘트 텍스트 생성 오류: {e}")
            return f"안녕하세요! {event.event_title} 골프 이벤트가 시작됩니다!"
    
    async def _generate_commentary_text(self, event: Event, commentary_count: int) -> str:
        """중계멘트 텍스트 생성"""
        try:
            prompt = f"""
            골프 이벤트 중계멘트를 작성해주세요.
            
            이벤트 정보:
            - 제목: {event.event_title}
            - 장소: {event.location or '미정'}
            - 중계멘트 순서: {commentary_count}번째
            
            요구사항:
            - 20-30초 내외의 길이
            - 골프 전문 캐스터 톤
            - 경기 상황에 대한 흥미로운 내용
            - 자연스럽고 생동감 있는 표현
            - 같은 문장을 두 번 이상 반복하지 마세요
            """
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 골프 전문 캐스터입니다. 생동감 있고 전문적인 중계멘트를 작성해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"중계멘트 텍스트 생성 오류: {e}")
            return f"현재 {event.event_title} 경기가 진행 중입니다. {commentary_count}번째 중계멘트입니다."
    
    async def _text_to_speech(self, text: str) -> bytes:
        """TTS로 오디오 생성"""
        try:
            logger.info("🔊 TTS INPUT TEXT (length=%d):\n%s", len(text), text)
            response = await asyncio.to_thread(
                self.openai_client.audio.speech.create,
                model="tts-1-hd",
                voice="alloy",
                input=text,
                response_format="mp3"
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"TTS 생성 오류: {e}")
            return b""
    
    def text_to_base64(self, audio_data: bytes) -> str:
        """오디오 데이터를 Base64로 인코딩"""
        try:
            return base64.b64encode(audio_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Base64 인코딩 오류: {e}")
            return ""

# 전역 AI 중계멘트 생성기 인스턴스
ai_commentary_generator = AICommentaryGenerator()

