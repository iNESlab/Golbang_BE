import logging
import asyncio
import aiohttp
from datetime import datetime
from django.conf import settings

logger = logging.getLogger(__name__)

class AICommentaryService:
    """
    OpenAI GPT API를 사용한 AI 해설 생성 서비스
    - 실제 GPT-4o-mini 모델 사용
    - API 키가 없거나 실패 시 더미 텍스트 사용
    """

    def __init__(self):
        # OpenAI API 키 확인
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY가 설정되지 않음. 더미 해설 사용")
        else:
            logger.info("🔑 OpenAI API 키 확인됨 (GPT 해설)")

    async def generate_opening_commentary(self, event, club_id: int):
        """이벤트 오프닝 해설 생성"""
        try:
            if not self.api_key:
                return await self._dummy_opening_text(event)
            
            # 이벤트 정보를 안전하게 가져오기
            event_info = await self._get_event_info(event)
            
            # 실제 데이터 가져오기
            recent_scores, leaderboard, recent_chats, scorecard = await self._get_real_data(event, club_id)
            
            prompt = f"""
당신은 전문 골프 중계방송 캐스터입니다. 골프 토너먼트의 오프닝 중계방송을 작성해주세요.

골프장: {event_info['location']}
날짜: {event_info['date']}
이벤트: {event_info['title']}
클럽: {event_info['club_name']}

현재 리더보드:
{leaderboard}

현재 스코어카드 (홀별 상세):
{scorecard}

시청자 채팅:
{recent_chats}

다음 형식으로 작성해주세요:
캐스터 박진우: [오프닝 멘트]

※ 반드시 실제 입력된 점수(홀별 타수, 파대비, 리더보드 등)만 바탕으로 해설하세요.
※ 입력 데이터에 없는 내용은 상상해서 넣지 마세요.
※ 실제 골프 방송처럼 생생하고 임팩트 있게 작성해주세요.
"""
            
            logger.info("🖋️ OPENING PROMPT:\n%s", prompt)
            text = await self._call_openai_gpt(prompt)
            if text:
                logger.info("📝 OPENING TEXT GENERATED:\n%s", text)
                logger.info("🎤 AI 오프닝 해설 생성: %s", text[:50] + "...")
                return text
            else:
                return await self._dummy_opening_text(event)
                
        except Exception as e:
            logger.error("AI 오프닝 해설 생성 오류: %s", e)
            return await self._dummy_opening_text(event)

    async def generate_event_commentary(self, event, club_id: int):
        """이벤트 중간 해설 생성"""
        try:
            if not self.api_key:
                return self._dummy_commentary_text(event)
            
            # 이벤트 정보를 안전하게 가져오기
            event_info = await self._get_event_info(event)
            
            from django.utils import timezone
            from channels.db import database_sync_to_async
            
            @database_sync_to_async
            def get_start_time():
                return event.start_date_time
            
            current_time = timezone.now()
            start_time = await get_start_time()
            elapsed_minutes = int((current_time - start_time).total_seconds() / 60) if start_time else 0
            
            # 실제 점수 데이터 가져오기
            recent_scores, leaderboard, recent_chats, scorecard = await self._get_real_data(event, club_id)
            logger.info("📊 실제 데이터 - 점수: %s", recent_scores)
            logger.info("🏆 실제 데이터 - 리더보드: %s", leaderboard) 
            logger.info("🃏 실제 데이터 - 스코어카드: %s", scorecard)
            logger.info("💬 실제 데이터 - 채팅: %s", recent_chats)
            logger.info("ℹ️ 이벤트 정보 - ID: %s, 제목: %s, 경과시간: %d분", event.id, event.event_title, elapsed_minutes)
            
            prompt = f"""
당신은 프로 골프 중계방송 캐스터입니다. 지난 1분간의 주요 점수 변화를 자연스럽게 중계해주세요.

※ 반드시 실제 입력된 점수 정보만 바탕으로 해설하세요.
※ 샷의 구체적 상황이나 현장에서 볼 수 있는 정보는 언급하지 마세요.
※ 입력 데이터에 없는 내용은 상상해서 넣지 마세요.
※ 채팅을 전부 다 읽어줄 필요는 없습니다. 재밌거나 임팩트 있는 것만 몇 개 골라서 자연스럽게 언급하세요. 다만 없는 채팅을 지어내지 마세요.
※ 생성되는 전체 중계방송 스크립트는 실제 사람이 읽었을 때 1분을 넘기면 안 됩니다. 너무 길게 작성하지 말고, 1분 이내에 읽을 수 있을 정도의 분량(최대 600~800자, 200~300단어)로 작성하세요.

이벤트 정보:
- 제목: {event.event_title}
- 경과 시간: 약 {elapsed_minutes}분
- 현재 시간: {timezone.localtime(current_time).strftime('%H시 %M분')}

지난 1분간의 점수 변화:
{recent_scores}

현재 리더보드:
{leaderboard}

현재 스코어카드 (홀별 상세):
{scorecard}

시청자 채팅:
{recent_chats}

점수 중계를 하면서 시청자들의 반응도 적절히 언급해주세요. 
예를 들어: 
- "선수의 멋진 플레이에 시청자분들도 환호하고 계시네요"
- "시청자분들도 이번 홀의 난이도를 체감하고 계시는 것 같습니다"
- "시청자분들의 반응이 뜨거우시네요!"

전문적이면서도 친근하고 재미있게 중계해주세요. 너무 딱딱하지 않게, 적절한 유머도 섞어주세요.
"""
            
            # 프롬프트 길이와 내용 확인
            prompt_length = len(prompt.strip())
            logger.info("📏 프롬프트 길이: %d 문자", prompt_length)
            if prompt_length < 100:
                logger.error("❌ 프롬프트가 너무 짧습니다! 내용: '%s'", prompt[:200])
            
            logger.info("🖋️ COMMENTARY PROMPT:\n%s", prompt)
            
            if not prompt.strip():
                logger.error("❌ 빈 프롬프트 감지! 더미 텍스트 반환")
                return self._dummy_commentary_text(event)
            
            text = await self._call_openai_gpt(prompt)
            if text:
                # 중복 텍스트 제거
                text = self._remove_duplicates(text)
                logger.info("📝 COMMENTARY TEXT GENERATED (after dedup):\n%s", text)
                logger.info("🎤 AI 중간 해설 생성: %s", text[:50] + "...")
                return text
            else:
                return self._dummy_commentary_text(event)
                
        except Exception as e:
            logger.error("AI 중간 해설 생성 오류: %s", e)
            return self._dummy_commentary_text(event)

    async def _get_real_data(self, event, club_id: int):
        """실제 점수, 리더보드, 채팅 데이터 가져오기"""
        from channels.db import database_sync_to_async
        from participants.models import HoleScore, Participant
        from chat.models import ChatMessage, ChatRoom
        from django.utils import timezone
        from datetime import timedelta
        
        try:
            # 지난 2분간의 점수 변화 (마지막 해설 이후)
            since_time = timezone.now() - timedelta(minutes=2)
            
            @database_sync_to_async
            def get_recent_scores():
                return list(HoleScore.objects.filter(
                    participant__event_id=event.id,
                    created_at__gte=since_time
                ).select_related('participant__club_member__user').order_by('-created_at')[:10])
            
            recent_scores_list = await get_recent_scores()
            
            if recent_scores_list:
                recent_scores = "\n".join([
                    f"• {score.participant.club_member.user.name} 선수: {score.hole_number}번홀 {score.score}타"
                    for score in recent_scores_list
                ])
            else:
                recent_scores = "점수 변화 없음"
            
            # 현재 리더보드 (전체 참가자)
            @database_sync_to_async
            def get_participants():
                return list(Participant.objects.filter(event_id=event.id).select_related('club_member__user'))
            
            participants_list = await get_participants()
            
            leaderboard_data = []
            scorecard_data = []
            
            for participant in participants_list:
                @database_sync_to_async
                def get_participant_scores(p):
                    return list(HoleScore.objects.filter(participant=p).order_by('hole_number'))
                
                scores_list = await get_participant_scores(participant)
                total_score = sum(score.score for score in scores_list) if scores_list else 0
                holes_played = len(scores_list)
                
                # 점수가 있는 참가자만 포함
                if holes_played > 0:
                    # 리더보드용 데이터
                    leaderboard_data.append({
                        'name': participant.club_member.user.name,
                        'total_score': total_score,
                        'holes_played': holes_played
                    })
                    
                    # 스코어카드용 데이터 (홀별 상세)
                    hole_details = ", ".join([
                        f"{score.hole_number}홀({score.score}타)"
                        for score in scores_list
                    ])
                    scorecard_data.append(f"{participant.club_member.user.name}: {hole_details} - 총 {total_score}타")
            
            # 점수순으로 정렬
            leaderboard_data.sort(key=lambda x: x['total_score'])
            
            # 점수가 있는 전체 참가자 리더보드 생성
            leaderboard = "\n".join([
                f"{i+1}. {p['name']} {p['total_score']}타 ({p['holes_played']}홀 완료)"
                for i, p in enumerate(leaderboard_data)
            ]) if leaderboard_data else "리더보드 정보 없음"
            
            # 스코어카드 생성
            scorecard = "\n".join(scorecard_data) if scorecard_data else "스코어카드 정보 없음"
            
            # 지난 2분간의 채팅 메시지
            try:
                # 클럽 채팅방 조회 (CLUB 타입)
                chat_room = await database_sync_to_async(ChatRoom.objects.get)(
                    club_id=club_id, chat_room_type='CLUB'
                )
                @database_sync_to_async
                def get_recent_chats():
                    return list(ChatMessage.objects.filter(
                        chat_room=chat_room,
                        created_at__gte=since_time
                    ).exclude(message_type='SYSTEM').select_related('sender').order_by('-created_at')[:5])
                
                recent_chats_list = await get_recent_chats()
                recent_chats = "\n".join([
                    f"• {chat.sender.name}: {chat.content}"
                    for chat in recent_chats_list
                ]) if recent_chats_list else "새로운 채팅 메시지 없음"
                
            except ChatRoom.DoesNotExist:
                recent_chats = "채팅방 정보 없음"
            
            return recent_scores, leaderboard, recent_chats, scorecard
            
        except Exception as e:
            logger.error("실제 데이터 가져오기 오류: %s", e)
            return "점수 변화 없음", "리더보드 정보 없음", "채팅 메시지 없음", "스코어카드 정보 없음"

    def _remove_duplicates(self, text: str) -> str:
        """GPT가 같은 내용을 두 번 반복하는 경우 제거"""
        try:
            text = text.strip()
            
            # 전체 텍스트가 정확히 두 번 반복된 경우 (A+A 패턴)
            half_len = len(text) // 2
            if half_len > 10:  # 최소 길이 체크
                first_half = text[:half_len].strip()
                second_half = text[half_len:].strip()
                if first_half == second_half:
                    logger.info("🔧 전체 중복 텍스트 제거: %d chars → %d chars", len(text), len(first_half))
                    return first_half
            
            # 문장 단위 중복 제거
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            unique_sentences = []
            seen = set()
            
            for sentence in sentences:
                # 비슷한 문장 체크 (70% 이상 유사하면 중복으로 간주)
                is_duplicate = False
                for existing in seen:
                    if len(sentence) > 5 and len(existing) > 5:
                        similarity = len(set(sentence) & set(existing)) / len(set(sentence) | set(existing))
                        if similarity > 0.7:
                            is_duplicate = True
                            break
                
                if not is_duplicate:
                    unique_sentences.append(sentence)
                    seen.add(sentence)
                else:
                    logger.info("🔧 중복 문장 제거: %s", sentence[:30] + "...")
            
            result = '. '.join(unique_sentences)
            if result and not result.endswith('.'):
                result += '.'
                
            return result if result else text
            
        except Exception as e:
            logger.error("중복 제거 오류: %s", e)
            return text

    async def _call_openai_gpt(self, prompt: str) -> str | None:
        """OpenAI GPT API 호출"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 200,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        text = data['choices'][0]['message']['content'].strip()
                        logger.info("✅ OpenAI GPT 성공: %d chars", len(text))
                        return text
                    else:
                        error_text = await response.text()
                        logger.error("❌ OpenAI GPT 실패 (%d): %s", response.status, error_text)
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("⏰ OpenAI GPT 타임아웃")
            return None
        except Exception as e:
            logger.error("❌ OpenAI GPT 오류: %s", e)
            return None

    async def _dummy_opening_text(self, event):
        """더미 오프닝 텍스트"""
        from django.utils import timezone
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def get_event_title():
            return getattr(event, 'event_title', '골프 토너먼트')
        
        event_title = await get_event_title()
        current_time = timezone.localtime(timezone.now())
        text = f"{event_title} 라디오 중계가 곧 시작됩니다! {current_time:%H:%M} 기준, 멋진 경기를 기대해주세요."
        logger.info("📢 더미 오프닝 텍스트: %s", text)
        return text

    async def _get_event_info(self, event):
        """이벤트 정보를 안전하게 가져오기"""
        from channels.db import database_sync_to_async
        
        @database_sync_to_async
        def get_info():
            return {
                'location': getattr(event, 'location', '미정'),
                'date': event.start_date_time.strftime('%Y년 %m월 %d일') if event.start_date_time else '미정',
                'title': getattr(event, 'event_title', '골프 토너먼트'),
                'club_name': event.club.name if event.club else '골프 클럽'
            }
        
        return await get_info()

    def _dummy_commentary_text(self, event):
        """더미 해설 텍스트"""
        from django.utils import timezone
        current_time = timezone.localtime(timezone.now())
        text = f"{current_time:%H:%M}, 현재 경기 중간 해설입니다. 멋진 플레이가 이어지고 있습니다!"
        logger.info("📢 더미 해설 텍스트: %s", text)
        return text
