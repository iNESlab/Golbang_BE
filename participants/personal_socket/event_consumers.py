import json
import logging
import asyncio
from dataclasses import dataclass, asdict

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from participants.personal_socket.mysql_interface import MySQLInterface
from participants.personal_socket.redis_interface import redis_client

@dataclass
class RankData:
    participant_id: int
    last_hole_number: int
    last_score: int
    rank: str
    handicap_rank: str
    sum_score: int
    handicap_score: int


# TODO: 유저 랭킹 변동 표시
class EventParticipantConsumer(AsyncWebsocketConsumer, MySQLInterface):
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
            logging.debug(f'Participant ID: {self.participant_id}')

            participant = await self.get_and_check_participant(self.participant_id, user)
            if participant is None:
                logging.info('No participant')
                await self.close(code=4004)
                return

            self.event_id = participant.event_id
            logging.debug(f'Event ID: {self.event_id}')

            self.group_name = self.get_event_group_name(self.event_id)
            logging.debug(f'Group Name: {self.group_name}')

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logging.info('WebSocket connection accepted')

            # 주기적으로 스코어를 전송하는 태스크를 설정
            self.send_task = asyncio.create_task(self.send_ranks_periodically())
            logging.debug('Started send_scores_periodically task')

        except Exception as e:
            logging.error(f'Error in connect: {e}')
            await self.send_json({'error': str(e)})
            await self.close(code=4005)

    async def disconnect(self, close_code):
        try:
            logging.info('Disconnecting WebSocket')

            if self.group_name:  # group_name이 None이 아닌지 확인
                await self.channel_layer.group_discard(self.group_name, self.channel_name)

            if hasattr(self, 'send_task'):
                self.send_task.cancel()  # 주기적인 태스크 취소
                logging.debug('Cancelled send_scores_periodically task')
        except Exception as e:
            logging.error(f'Error in disconnect: {e}')

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            text_data_json = json.loads(text_data)
            sort = text_data_json['sort']
            if sort == 'sum_score':
                await self.send_ranks()
            else:
                await self.send_ranks(sort)

        except Exception as e:
            logging.error(f'error in receive: {e}')
            await self.send_json({'status': 400, 'message': str(e)})

    @staticmethod
    def get_event_group_name(event_id):
        return f"event_{event_id}_group_all"

    async def send_ranks(self, sort='sum_score'):
        try:
            # 모든 참가자와 관련된 정보를 한 번의 쿼리로 가져옴
            participants = await self.get_event_participants(self.event_id)
            logging.info('participants: {}'.format(participants))

            ranks = await asyncio.gather(*[
                self.process_participant(participant) for participant in participants
            ])

            # sum_score 기준으로 정렬
            ranks_sorted = sorted(ranks, key=lambda x: x[sort], reverse=False)
            logging.info(f'ranks_sorted: {ranks_sorted}')

            await self.send_json(ranks_sorted)
        except Exception as e:
            await self.send_json({'error': '스코어 기록을 가져오는 데 실패했습니다.'})

    async def process_participant(self, participant):
        participant_id = participant.id
        rank_data = await self.get_event_rank_from_redis(participant_id)
        user = participant.club_member.user

        return {
            'user': {
                'name': user.name
                # TODO 'image' : 유저 프로필 사진 추가
            },
            **asdict(rank_data)  # RankData 객체를 딕셔너리로 변환 후 펼침
        }

    async def get_event_rank_from_redis(self, participant_id):
        logging.info('Fetching hole scores from Redis')
        redis_key = f'participant:{participant_id}'

        rank = await sync_to_async(redis_client.hget)(redis_key, "rank")
        handicap_rank = await sync_to_async(redis_client.hget)(redis_key, "handicap_rank")
        sum_score = await sync_to_async(redis_client.hget)(redis_key, "sum_score")
        handicap_score = await sync_to_async(redis_client.hget)(redis_key, "handicap_score")

        # 홀 번호와 점수를 저장하기 위한 초기 변수 설정
        last_hole_number = 0
        last_score = 0

        # 홀 점수를 가져오기 위해 Redis에서 모든 홀 데이터를 가져옴
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)

        if keys:
            # keys를 내림차순으로 정렬
            keys.sort(reverse=True, key=lambda k: int(k.decode('utf-8').split(':')[-1]))

            # 가장 큰 hole_number와 그에 해당하는 score를 가져옴
            last_key = keys[0]
            last_hole_number = int(last_key.decode('utf-8').split(':')[-1])
            last_score = int(await sync_to_async(redis_client.get)(last_key))

        return RankData(
            participant_id=participant_id,
            last_hole_number=last_hole_number,
            last_score=last_score,
            rank=rank.decode('utf-8') if rank else None,
            handicap_rank=handicap_rank.decode('utf-8') if handicap_rank else None,
            sum_score=int(sum_score) if sum_score else 0,
            handicap_score=int(handicap_score) if handicap_score else 0
        )

    async def send_ranks_periodically(self):
        logging.info('send_scores_periodically started')
        while True:
            try:
                await self.send_ranks()

            except Exception as e:
                logging.error(f'Error in send_scores_periodically: {e}')
                await self.send_json({'error': '주기적인 스코어 전송 실패', 'details': str(e)})
            await asyncio.sleep(300)  # 5분마다 주기적으로 스코어 전송

    async def send_json(self, content):
        try:
            logging.debug(f'Sending JSON: {content}')
            await self.send(text_data=json.dumps(content, ensure_ascii=False))
            logging.debug('JSON sent successfully')
        except Exception as e:
            logging.error(f'Error in send_json: {e}')
