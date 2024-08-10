import json
import redis
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from events.models import Event
from participants.models import Participant, HoleScore

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class GroupParticipantConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.participant_id = None
        self.group_type = None
        self.event_id = None
        self.group_name = None

    async def connect(self):
        try:
            user = self.scope['user']
            self.participant_id = self.scope['url_route']['kwargs']['participant_id']
            participant = await self.get_and_check_participant(self.participant_id, user)

            if participant is None:
                logger.info('participant not found or not match with user token')
                await self.close(code = 400)
                return

            self.group_type = participant.group_type

            self.event_id = await self.get_event_id(participant)

            self.group_name = self.get_group_name(self.event_id)

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # 주기적으로 스코어를 전송하는 태스크를 설정
            self.send_task = asyncio.create_task(self.send_scores_periodically())

        except ValueError as e:
            await self.close_with_status(500, str(e))

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.transfer_scores_to_mysql()
            self.send_task.cancel()  # 주기적인 태스크 취소
        except Exception as e:
            pass

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            text_data_json = json.loads(text_data)

            if text_data_json['action'] == 'get':
                await self.send_scores()
                return

            self.participant_id = text_data_json['participant_id']
            hole_number = text_data_json['hole_number']
            score = text_data_json['score']

            participant = await self.get_participant(self.participant_id)
            if not participant:
                await self.send_json(self.handle_404_not_found('Participant', self.participant_id))
                return

            if hole_number is None or score is None:
                await self.send_json({'status': 400, 'message': "Both hole number and score are required."})
                return

            await self.update_hole_score_in_redis(self.participant_id, hole_number, score)
            await self.update_participant_sum_score(self.participant_id)

            await self.channel_layer.group_send(self.group_name, {
                'type': 'input_score',
                'participant_id': self.participant_id,
                'hole_number': hole_number,
                'score': score,
                'sum_score': participant.sum_score,
            })
        except ValueError as e:
            await self.send_json({'status': 400, 'message': str(e)})

    @staticmethod
    def get_group_name(event_id):
        return f"event_room_{event_id}"

    async def close_with_status(self, code, message):
        await self.send_json({'status': code, 'message': message})
        await self.close(code=code)

    def handle_404_not_found(self, model_name, pk):
        return {
            'status': 404,
            'message': f'{model_name} {pk} is not found'
        }

    async def update_hole_score_in_redis(self, participant_id, hole_number, score):
        key = f'participant:{participant_id}:hole:{hole_number}'
        await sync_to_async(redis_client.set)(key, score)
        await sync_to_async(redis_client.expire)(key, 259200)  # 3일(259200초) 후에 자동으로 삭제되도록 TTL 설정

    async def update_participant_sum_score(self, participant_id):
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)

        sum_score = 0
        for key in keys:
            score = await sync_to_async(redis_client.get)(key)
            sum_score += int(score)

        await self.update_participant_sum_score_in_db(participant_id, sum_score)

    async def input_score(self, event):
        try:
            participant_id = event['participant_id']
            hole_number = event['hole_number']
            score = event['score']
            sum_score = event['sum_score']
            await self.send_json({'participant_id': participant_id, 'hole_number': hole_number, 'score': score, 'sum_score': sum_score})
        except Exception as e:
            await self.send_json({'error': '메시지 전송 실패'})

    async def transfer_scores_to_mysql(self):
        keys_pattern = f'participant:{self.participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)

        async def update_or_create_hole_score(key):
            hole_number = int(key.decode('utf-8').split(':')[-1])
            score = int(await sync_to_async(redis_client.get)(key))

            await self.update_or_create_hole_score_in_db(self.participant_id, hole_number, score)

        await asyncio.gather(*(update_or_create_hole_score(key) for key in keys))

    async def send_scores(self):
        try:
            # 그룹에 속한 모든 참가자 ID를 한 번의 쿼리로 가져옴
            participants = await self.get_group_participants(self.event_id, self.group_type)

            # 각 참가자의 홀 스코어를 비동기로 병렬 처리
            group_scores = await asyncio.gather(*[
                self.process_participant(participant) for participant in participants
            ])

            await self.send_json(group_scores)
        except Exception as e:
            await self.send_json({'error': '스코어 기록을 가져오는 데 실패했습니다.'})

    async def process_participant(self, participant):
        participant_id = participant.id
        hole_scores = await self.get_all_hole_scores_from_redis(participant_id)

        return {
            'user_name': participant.club_member.user.name,
            'participant_id': participant_id,
            'scores': hole_scores
        }


    @database_sync_to_async
    def get_and_check_participant(self, participant_id, user):
        try:
            participant = Participant.objects.select_related('club_member__user').get(id=participant_id)
            if participant.club_member.user != user:
                return None
            return participant
        except Participant.DoesNotExist:
            return None

    @database_sync_to_async
    def get_participant(self, participant_id):
        try:
            return Participant.objects.select_related('club_member__user').get(id=participant_id)
        except Participant.DoesNotExist:
            return None

    @database_sync_to_async
    def get_event(self, event_id):
        try:
            return Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return None

    @database_sync_to_async
    def check_event_exists(self, event_id):
        return Event.objects.filter(id=event_id).exists()

    @database_sync_to_async
    def update_participant_sum_score_in_db(self, participant_id, sum_score):
        Participant.objects.filter(id=participant_id).update(sum_score=sum_score)

    @database_sync_to_async
    def update_or_create_hole_score_in_db(self, participant_id, hole_number, score):
        return HoleScore.objects.update_or_create(
            participant_id=participant_id,
            hole_number=hole_number,
            defaults={'score': score}
        )

    @database_sync_to_async
    def get_group_participants(self, event_id, group_type=None):
        if group_type is None:
            raise ValueError("Group type is missing")
        return list(Participant.objects
                    .filter(event_id=event_id, group_type=group_type)
                    .select_related('club_member__user'))

    async def get_all_hole_scores_from_redis(self, participant_id):
        logger.info('participant_id: %s', participant_id)
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)
        hole_scores = []
        for key in keys:
            logger.info('hole_scores: %s', hole_scores)
            hole_number = int(key.decode('utf-8').split(':')[-1])
            score = int(await sync_to_async(redis_client.get)(key))
            logger.info('score: %s', score)
            hole_scores.append({'hole_number': hole_number, 'score': score})
        return hole_scores

    @database_sync_to_async
    def get_event_id(self, participant):
        return participant.event.id

    async def send_json(self, content):
        try:
            logger.debug(f'Sending JSON: {content}')
            await self.send(text_data=json.dumps(content, ensure_ascii=False))
            logger.debug('JSON sent successfully')
        except Exception as e:
            logger.error(f'Error in send_json: {e}')

    async def send_scores_periodically(self):
        while True:
            try:
                await self.send_scores()
            except Exception as e:
                await self.send_json({'status': 500, 'message': str(e)})
            await asyncio.sleep(300)  # 5분마다 주기적으로 스코어 전송