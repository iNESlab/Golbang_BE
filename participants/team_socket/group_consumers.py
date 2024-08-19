import json
import logging
import asyncio
from dataclasses import dataclass, asdict

from channels.generic.websocket import AsyncWebsocketConsumer

from participants.models import Participant
from participants.team_socket.mysql_interface import MySQLInterface
from participants.team_socket.redis_interface import RedisInterface


@dataclass
class ResponseData:
    participant_id: int
    group_type: chr
    team_type: chr
    is_group_win: bool
    is_group_win_handicap: bool
    hole_number: int
    score: int
    sum_score: int
    handicap_score: int


class GroupParticipantConsumer(AsyncWebsocketConsumer, RedisInterface, MySQLInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.participant_id = None
        self.group_type = None
        self.team_type = None
        self.event_id = None
        self.group_name = None

    async def connect(self):
        try:
            user = self.scope['user']
            self.participant_id = self.scope['url_route']['kwargs']['participant_id']
            participant = await self.get_and_check_participant(self.participant_id, user)

            if participant is None:
                logging.info('participant not found or not match with user token')
                await self.close(code=400)
                return

            self.group_type = participant.group_type
            self.event_id = participant.event_id
            self.group_name = self.get_group_name(self.event_id, self.group_type)

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
            await self.transfer_game_data_to_db()
            self.send_task.cancel()  # 주기적인 태스크 취소
        except Exception as e:
            pass

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            text_data_json = json.loads(text_data)

            if text_data_json['action'] == 'get':
                await self.send_scores()
                return

            participant_id = text_data_json['participant_id'] # request body로 받는 참가자id
            hole_number = text_data_json['hole_number']
            score = text_data_json['score']

            participant = await self.get_participant(participant_id)
            if not participant:
                await self.send_json(self.handle_404_not_found('Participant', participant_id))
                return

            if hole_number is None or score is None:
                await self.send_json({'status': 400, 'message': "Both hole number and score are required."})
                return

            await self.update_hole_score_in_redis(participant_id, hole_number, score)
            await self.update_participant_sum_and_handicap_score_in_redis(participant)
            logging.info(f'isTeam? {participant.team_type != Participant.TeamType.NONE}')
            if participant.team_type != Participant.TeamType.NONE:
                logging.info(f'참가자는 팀에 있습니다.')
                # 조별 승리 여부 갱신
                await self.update_is_group_win_in_redis(participant)
                # 전체 이벤트 승리 팀 갱신
                await self.update_event_win_team_in_redis(participant.event_id)

            # Redis에서 갱신된 sum_score와 handicap_score, is_group_win, is_group_win_handicap을 가져오기
            sum_score, handicap_score, is_group_win, is_group_win_handicap = await self.get_scores_from_redis(participant)

            response_data = ResponseData(
                participant_id=participant_id,
                hole_number=hole_number,           # 사용자 입력
                group_type=participant.group_type, # mysql에서 가져옴
                team_type=participant.team_type,   # mysql에서 가져옴
                is_group_win=is_group_win,
                is_group_win_handicap=is_group_win_handicap,
                score=score,                       # 사용자 입력
                sum_score=sum_score,
                handicap_score=handicap_score
            )

            await self.channel_layer.group_send(self.group_name, {
                'type': 'input_score',
                **asdict(response_data)  # Send all response data
            })
        except ValueError as e:
            await self.send_json({'status': 400, 'message': str(e)})

    @staticmethod
    def get_group_name(event_id, group_type):
        return f"event_{event_id}_group_{group_type}_room"

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
            response_data = ResponseData(
                participant_id=event['participant_id'],
                hole_number=event['hole_number'],
                group_type=event['group_type'],
                team_type=event['team_type'],
                is_group_win=event['is_group_win'],
                is_group_win_handicap=event['is_group_win_handicap'],
                score=event['score'],
                sum_score=event['sum_score'],
                handicap_score=event['handicap_score']
            )

            await self.send_json(asdict(response_data))
        except Exception as e:
            await self.send_json({'error': '메시지 전송 실패'})

    async def send_scores(self):
        try:
            # 그룹에 속한 모든 참가자를 한 번의 쿼리로 가져옴
            participants = await self.get_participants_from_redis(self.event_id,self.group_type)
            logging.info(f'participants: {participants}')
            # 각 참가자의 홀 스코어를 비동기로 병렬 처리
            group_scores = await asyncio.gather(*[
                self.process_participant(participant) for participant in participants
            ])
            logging.info(f'group_scores: {group_scores}')

            await self.send_json(group_scores)
        except Exception as e:
            await self.send_json({'error': '스코어 기록을 가져오는 데 실패했습니다.'})

    async def process_participant(self, participant):
        participant_id = participant.id
        hole_scores = await self.get_all_hole_scores_from_redis(participant_id)
        logging.info(f'hole_scores:{hole_scores}')
        return {
            'participant_id': participant_id,
            'group_type': participant.group_type,
            'team_type': participant.team_type,
            'is_group_win': participant.is_group_win,
            'is_group_win_handicap': participant.is_group_win_handicap,
            'sum_score':participant.sum_score,
            'handicap_score': participant.handicap_score,
            'scores': hole_scores,
        }

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