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
    async def connect(self):
        try:
            self.participant_id = self.scope['url_route']['kwargs']['participant_id']
            logger.debug(f'Participant ID: {self.participant_id}')

            participant = await self.get_participant(self.participant_id)
            if participant is None:
                raise ValueError('참가자가 존재하지 않습니다.')

            self.event_id = await self.get_event_id(self.participant_id)
            logger.debug(f'Event ID: {self.event_id}')

            self.group_name = self.get_event_group_name(self.event_id)
            logger.debug(f'Group Name: {self.group_name}')

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info('WebSocket connection accepted')

            # 주기적으로 스코어를 전송하는 태스크를 설정
            self.send_task = asyncio.create_task(self.send_scores_periodically())
            logger.debug('Started send_scores_periodically task')

        except Exception as e:
            logger.error(f'Error in connect: {e}')
            await self.send_json({'error': str(e)})
            await self.close()

    async def disconnect(self, close_code):
        try:
            logger.info('Disconnecting WebSocket')
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

    async def send_scores(self, participant_id_list):
        try:
            all_scores = []
            for participant_id in participant_id_list:
                hole_scores = await self.get_all_hole_scores_from_redis(participant_id)
                all_scores.append({
                    'participant_id': participant_id,
                    'scores': hole_scores
                })
            await self.send_json(all_scores)
        except Exception as e:
            await self.send_json({'error': '스코어 기록을 가져오는 데 실패했습니다.'})

    async def send_scores_periodically(self):
        logger.info('send_scores_periodically started')
        while True:
            try:
                logger.info('Fetching participants...')
                participants = await self.get_all_participants(self.event_id)
                participants_list = await sync_to_async(list)(participants.values_list('id', flat=True))
                logger.info('participants_list', participants_list)
                await self.send_scores(participants_list)
            except Exception as e:
                logger.error(f'Error in send_scores_periodically: {e}')
                await self.send_json({'error': '주기적인 스코어 전송 실패', 'details': str(e)})
            await asyncio.sleep(10)  # 10초마다 주기적으로 스코어 전송

    async def get_all_hole_scores_from_redis(self, participant_id):
        logger.info('Fetching hole scores from Redis')
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)
        logger.debug(f'Keys: {keys}')
        hole_scores = []
        for key in keys:
            logger.debug(f'Processing key: {key}')
            hole_number = int(key.decode('utf-8').split(':')[-1])
            score = int(await sync_to_async(redis_client.get)(key))
            logger.debug(f'Hole number: {hole_number}, score: {score}')
            hole_scores.append({'hole_number': hole_number, 'score': score})
        return hole_scores

    async def send_json(self, content):
        logger.debug(f'Sending JSON: {content}')
        await self.send(text_data=json.dumps(content))