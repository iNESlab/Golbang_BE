import json
import redis
import logging
import asyncio

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from participants.models import Participant

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # 수정된 부분
handler.setFormatter(formatter)
logger.addHandler(handler)


class EventParticipantConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.participant_id = None
        self.group_name = None
        self.event_id = None

    async def connect(self):
        try:
            user = self.scope.get('user', None)

            if user is None or user.is_anonymous:
                # await self.send_json({'error': "Authentication required"})
                # accept 전까지는 send_json을 사용하지 못함 => 이는 구체적인 에러 메시지를 못만듬
                await self.close(code=4001)
                return

            self.participant_id = self.scope['url_route']['kwargs']['participant_id']
            logger.debug(f'Participant ID: {self.participant_id}')

            participant = await self.get_participant(self.participant_id)
            if participant is None:
                logging.info('No participant')
                await self.close(code=4004)
                return

            self.event_id = await self.get_event_id(self.participant_id)
            logger.debug(f'Event ID: {self.event_id}')

            self.group_name = self.get_event_group_name(self.event_id)
            logger.debug(f'Group Name: {self.group_name}')

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info('WebSocket connection accepted')

            # 주기적으로 스코어를 전송하는 태스크를 설정
            self.send_task = asyncio.create_task(self.send_ranks_periodically())
            logger.debug('Started send_scores_periodically task')

        except Exception as e:
            logger.error(f'Error in connect: {e}')
            await self.send_json({'error': str(e)})
            await self.close(code=4005)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        await self.send_ranks()

    async def disconnect(self, close_code):
        try:
            logger.info('Disconnecting WebSocket')

            if self.group_name:  # group_name이 None이 아닌지 확인
                await self.channel_layer.group_discard(self.group_name, self.channel_name)

            if hasattr(self, 'send_task'):
                self.send_task.cancel()  # 주기적인 태스크 취소
                logger.debug('Cancelled send_scores_periodically task')
        except Exception as e:
            logger.error(f'Error in disconnect: {e}')

    @database_sync_to_async
    def get_participant(self, participant_id):
        try:
            return Participant.objects.get(id=participant_id)
        except Participant.DoesNotExist:
            return None

    @staticmethod
    def get_event_group_name(event_id):
        return f"event_{event_id}_group_all"

    @database_sync_to_async
    def get_event_id(self, participant_id):
        participant = Participant.objects.get(id=participant_id)
        return participant.event_id

    @database_sync_to_async
    def get_all_participants(self, event_id):
        return Participant.objects.filter(event_id=event_id)

    @database_sync_to_async
    def get_user_from_participant(self, participant_id):
        participant = Participant.objects.get(id=participant_id)
        return participant.club_member.user

    async def send_ranks(self):
        try:
            # 모든 참가자와 관련된 정보를 한 번의 쿼리로 가져옴
            participants = await sync_to_async(list)(
                Participant.objects.filter(event_id=self.event_id).select_related('club_member__user')
            )

            ranks = await asyncio.gather(*[
                self.process_participant(participant) for participant in participants
            ])

            # sum_score 기준으로 정렬
            ranks_sorted = sorted(ranks, key=lambda x: x['sum_score'], reverse=False)

            await self.send_json(ranks_sorted)
        except Exception as e:
            await self.send_json({'error': '스코어 기록을 가져오는 데 실패했습니다.'})

    async def process_participant(self, participant):
        participant_id = participant.id
        hole_number, sum_score = await self.get_event_rank_from_redis(participant_id)
        user = participant.club_member.user

        return {
            'user': {
                'name': user.name
                # TODO 'image' : 유저 프로필 사진 추가
            },
            'participant_id': participant_id,
            'hole_number': hole_number,
            'sum_score': sum_score,
            'handicap_score': sum_score + user.handicap
            # 등수는 프론트에서... sum_score냐 handicap_score냐에 따라 정렬 방법과 순위가 달라짐
        }

    async def get_event_rank_from_redis(self, participant_id):
        logger.info('Fetching hole scores from Redis')
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)
        logger.debug(f'Keys: {keys}')

        last_hole_number = 0
        total_score = 0

        for key in keys:
            logger.debug(f'Processing key: {key}')
            hole_number = int(key.decode('utf-8').split(':')[-1])
            score = int(await sync_to_async(redis_client.get)(key))
            logger.debug(f'Hole number: {hole_number}, score: {score}')

            total_score += score
            if hole_number > last_hole_number:
                last_hole_number = hole_number

        return last_hole_number, total_score

    async def send_ranks_periodically(self):
        logger.info('send_scores_periodically started')
        while True:
            try:
                await self.send_ranks()

            except Exception as e:
                logger.error(f'Error in send_scores_periodically: {e}')
                await self.send_json({'error': '주기적인 스코어 전송 실패', 'details': str(e)})
            await asyncio.sleep(300)  # 5분마다 주기적으로 스코어 전송

    async def send_json(self, content):
        try:
            logger.debug(f'Sending JSON: {content}')
            await self.send(text_data=json.dumps(content, ensure_ascii=False))
            logger.debug('JSON sent successfully')
        except Exception as e:
            logger.error(f'Error in send_json: {e}')