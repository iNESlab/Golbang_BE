import json
import logging
import asyncio

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from participants.socket.mysql_interface import MySQLInterface
from participants.socket.redis_interface import RedisInterface, redis_client


class GroupParticipantConsumer(AsyncWebsocketConsumer, RedisInterface, MySQLInterface):
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
                await self.close(code=400)
                return

            self.group_type = participant.group_type

            self.event_id = participant.event_id

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
            # Redis에서 데이터를 가져와 MySQL로 전송
            await self.transfer_scores_and_ranks_to_mysql()
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
            await self.update_participant_sum_and_handicap_score_in_redis(participant)

            await self.channel_layer.group_send(self.group_name, {
                'type': 'input_score',
                'participant_id': self.participant_id,
                'hole_number': hole_number,
                'score': score,
                'sum_score': participant.sum_score,
                'handicap_score': participant.handicap_score
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

    async def input_score(self, event):
        try:
            participant_id = event['participant_id']
            hole_number = event['hole_number']
            score = event['score']
            sum_score = event['sum_score']
            handicap_score = event['handicap_score']

            await self.send_json({'participant_id': participant_id, 'hole_number': hole_number, 'score': score,
                                  'sum_score': sum_score, 'handicap_score': handicap_score})
        except Exception as e:
            await self.send_json({'error': '메시지 전송 실패'})

    async def transfer_scores_and_ranks_to_mysql(self):
        participants = await self.get_event_participants(self.event_id)
        for participant in participants:
            # 전체 참가자들의 랭킹 정보를 업데이트
            redis_key = f'participant:{participant.id}'
            logging.info('redis_key: %s', redis_key)
            rank = await sync_to_async(redis_client.hget)(redis_key, "rank")
            handicap_rank = await sync_to_async(redis_client.hget)(redis_key, "handicap_rank")
            sum_score = await sync_to_async(redis_client.hget)(redis_key, "sum_score")
            handicap_score = await sync_to_async(redis_client.hget)(redis_key, "handicap_score")

            # 가져온 데이터를 문자열로 변환
            rank = rank.decode('utf-8') if rank else None
            handicap_rank = handicap_rank.decode('utf-8') if handicap_rank else None
            sum_score = sum_score.decode('utf-8') if sum_score else None
            handicap_score = handicap_score.decode('utf-8') if handicap_score else None

            if rank is not None and handicap_rank is not None:
                # MySQL에 rank와 handicap_rank 업데이트
                await self.update_participant_rank_in_db(participant.id, rank, handicap_rank, sum_score, handicap_score)

            # hole scores를 가져오기 위해 별도의 패턴으로 검색
            score_keys_pattern = f'participant:{participant.id}:hole:*'
            score_keys = await sync_to_async(redis_client.keys)(score_keys_pattern)
            logging.info('score_keys: %s', score_keys)

            # 각 홀에 대한 점수를 비동기로 병렬 처리하여 DB에 저장
            async def update_or_create_hole_score(key):
                hole_number = int(key.decode('utf-8').split(':')[-1])
                score = int(await sync_to_async(redis_client.get)(key))
                await self.update_or_create_hole_score_in_db(participant.id, hole_number, score)

            await asyncio.gather(*(update_or_create_hole_score(key) for key in score_keys))

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

    def assign_ranks(self, participants, rank_type):
        """
        participants 리스트를 정렬된 순서로 받아, 해당 기준으로 순위를 할당.
        rank_type에 따라 일반 rank 또는 handicap_rank를 설정.
        """
        previous_score = None
        rank = 1
        tied_rank = 1  # 동점자의 랭크를 별도로 관리
        logging.info(f'===={rank_type}====')
        for idx, participant in enumerate(participants):
            logging.info(f'participant{idx}: {participant}')
            current_score = getattr(participant, rank_type.replace('rank', 'score'))
            logging.info(f'previous_score: {previous_score}, current_score: {current_score}')
            # 순위 할당
            if current_score == previous_score:
                setattr(participant, rank_type, f"T{tied_rank}")  # 이전 참가자와 동일한 점수라면 T로 표기
                logging.info(f'current P: rank: {participant.rank}, handicap_rank: {participant.handicap_rank}')
                setattr(participants[idx - 1], rank_type, f"T{tied_rank}")  # 이전 참가자의 랭크도 T로 업데이트
                logging.info(
                    f'previous P: rank: {participants[idx - 1].rank}, handicap_rank: {participants[idx - 1].handicap_rank}')

            else:
                if 'sum_rank' == rank_type:
                    setattr(participant, 'rank', str(rank))
                else:
                    setattr(participant, rank_type, str(rank))  # 새로운 점수일 경우 일반 순위

                logging.info(f'current P: rank: {participant.rank}, handicap_rank: {participant.handicap_rank}')
                tied_rank = rank  # 새로운 점수에서 동점 시작 지점을 설정

            previous_score = current_score
            rank += 1  # 다음 순위로 이동

    async def get_all_hole_scores_from_redis(self, participant_id):
        logging.info('participant_id: %s', participant_id)
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)
        hole_scores = []
        for key in keys:
            logging.info('hole_scores: %s', hole_scores)
            hole_number = int(key.decode('utf-8').split(':')[-1])
            score = int(await sync_to_async(redis_client.get)(key))
            logging.info('score: %s', score)
            hole_scores.append({'hole_number': hole_number, 'score': score})
        return hole_scores

    async def send_json(self, content):
        try:
            logging.debug(f'Sending JSON: {content}')
            await self.send(text_data=json.dumps(content, ensure_ascii=False))
            logging.debug('JSON sent successfully')
        except Exception as e:
            logging.error(f'Error in send_json: {e}')

    async def send_scores_periodically(self):
        while True:
            try:
                await self.send_scores()
            except Exception as e:
                await self.send_json({'status': 500, 'message': str(e)})
            await asyncio.sleep(300)  # 5분마다 주기적으로 스코어 전송