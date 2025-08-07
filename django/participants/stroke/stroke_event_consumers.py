'''
MVP demo ver 0.0.3
2024.08.23
participa/stroke/stroke_event_consumer.py

전체 현황 조회
'''
import json
import logging
import asyncio
from dataclasses import asdict
from typing import List

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from participants.models import Participant
from participants.stroke.data_class import ParticipantRedisData, RankResponseData
from participants.stroke.mysql_interface import MySQLInterface
from participants.stroke.redis_interface import redis_client, RedisInterface


# TODO: 유저 랭킹 변동 표시
class EventParticipantConsumer(AsyncWebsocketConsumer, MySQLInterface, RedisInterface):
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
                # 즉, 인증이 되지 않은 사용자는 연결을 거부
                await self.close(code=4001) # TODO: 에러코드가 잘 나오도록 보완이 필요함
                return

            self.participant_id = self.scope['url_route']['kwargs']['participant_id']
            logging.debug(f'Participant ID: {self.participant_id}')

            participant: ParticipantRedisData = await self.get_participant_from_redis(self.event_id,self.participant_id) # redis에서 참가자 정보 가져오기
            
            if participant is None:
                logging.info('No participant')
                await self.send_json({'status': 404, 'error': f"Participant[{self.participant_id}] not found"})
                await self.close(code=404)
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
            await self.send_json({'status': 500, 'error': str(e)})
            await self.close(code=5000)

    async def disconnect(self, close_code):
        try:
            logging.info('Disconnecting WebSocket')

            if self.group_name:  # group_name이 None이 아닌지 확인
                await self.channel_layer.group_discard(self.group_name, self.channel_name)

            if hasattr(self, 'send_task'):
                self.send_task.cancel()  # 주기적인 태스크 취소
                logging.debug('Cancelled send_scores_periodically task')
        except Exception as e:
            await self.send_json({'status': 500, 'error': str(e)})
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
            await self.send_json({'status': 400, 'error': str(e)})

    @staticmethod
    def get_event_group_name(event_id):
        return f"event_{event_id}_group_all"

    async def send_ranks(self, sort='sum_score'):
        try:
            event_data = await self.get_event_data_from_redis(self.event_id)
            # 모든 참가자와 관련된 정보를 한 번의 쿼리로 가져옴
            participants: List[ParticipantRedisData] = await self.get_event_participants_from_redis(self.event_id)
            logging.info('participants: {}'.format(participants))

            ranks = await asyncio.gather(*[
                self.process_participant(participant) for participant in participants
            ])

            # None이 아닌 값만 필터링하여 ranks 리스트에 포함
            ranks = [rank for rank in ranks if rank is not None]

            # sum_score 기준으로 정렬
            ranks_sorted = sorted(ranks, key=lambda x: x[sort], reverse=False)
            logging.info(f'ranks_sorted: {ranks_sorted}')

            # 최종 JSON 구조 생성
            response_data = {
                'event': {**asdict(event_data)},  # 상단에 Event 정보를 포함
                'rankings': ranks_sorted  # 그 아래에 랭킹 정보 표시
            }
            print(f'response_data: {response_data}')
            await self.send_json(response_data)
        except Exception as e:
            await self.send_json({'status':500,'error': f'스코어 기록을 가져오는 데 실패했습니다.{e}'})

    async def process_participant(self, participant: ParticipantRedisData):
        # 참가자 데이터를 처리하여 rank 정보를 반환

        rank_data = await self.get_event_rank_from_redis(participant.event_id, participant)

        # 아직 점수 입력을 하지 않은 참가자 정보 제외
        if rank_data.last_hole_number == 0:
            return None

        return {
            'user': {
                'name': participant.user_name,
                'profile_image' : participant.profile_image,
            },
            **asdict(rank_data)  # RankData 객체를 딕셔너리로 변환 후 펼침
        }

    async def get_event_rank_from_redis(self, event_id, participant: ParticipantRedisData):
        # Redis에서 참가자의 랭킹 정보를 가져옴

        logging.info('Fetching hole scores from Redis')
        participant_id = participant.participant_id

        # 홀 번호와 점수를 저장하기 위한 초기 변수 설정
        last_hole_number = 0
        last_score = 0

        # 홀 점수를 가져오기 위해 Redis에서 모든 홀 데이터를 가져옴
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)

        if keys:
            # keys를 내림차순으로 정렬
            keys.sort(reverse=True, key=lambda k: int(k.split(':')[-1]))

            # 가장 큰 hole_number와 그에 해당하는 score를 가져옴
            last_key = keys[0]
            last_hole_number = int(last_key.split(':')[-1])
            last_score = int(await sync_to_async(redis_client.get)(last_key))

        return RankResponseData(
            participant_id=participant_id,
            last_hole_number=last_hole_number,
            last_score=last_score,
            rank=participant.rank,
            handicap_rank=participant.handicap_rank,
            sum_score=participant.sum_score,
            handicap_score=participant.handicap_score,
        )

    async def send_ranks_periodically(self):
        # 주기적으로 참가자들의 점수 전송

        logging.info('send_scores_periodically started')
        while True:
            try:
                await self.send_ranks()

            except Exception as e:
                logging.error(f'Error in send_scores_periodically: {e}')
                await self.send_json({'status':500, 'error': '주기적인 스코어 전송 실패', 'details': str(e)})
            await asyncio.sleep(300)  # 5분마다 주기적으로 스코어 전송

    async def send_json(self, content):
        # JSON 데이터를 WebSocket을 통해 전송

        try:
            logging.debug(f'Sending JSON: {content}') 
            #TODO: 응답할 때, 아래처럼 보내도록 변경 지금은 날것으로 보내고 있어서 프론트에서 에러핸들링하기 어려움
            '''
            await self.send_json({
                'status': 200,
                'message': 'success',
                'data': content
            })
            '''
            await self.send(text_data=json.dumps(content, ensure_ascii=False))
            logging.debug('JSON sent successfully')
        except Exception as e:
            logging.error(f'Error in send_json: {e}')
            await self.send_json({'status':500, 'error': f'Error in send_json: {e}'})
