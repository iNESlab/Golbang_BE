'''
MVP demo ver 0.0.3
2024.08.23
participa/stroke/stroke_group_consumer.py

스코어카드(그룹별 현황 조회) / 그룹 내 참가자들의 점수를 실시간으로 관리
'''
import json
import logging
import asyncio
from dataclasses import asdict

from channels.generic.websocket import AsyncWebsocketConsumer

from participants.models import Participant
from participants.stroke.data_class import ParticipantRedisData
from participants.stroke.mysql_interface import MySQLInterface
from participants.stroke.redis_interface import RedisInterface
from participants.tasks import save_event_periodically_task

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

            participant: ParticipantRedisData = await self.get_participant_from_redis(self.event_id,self.participant_id) # redis에서 참가자 정보 가져오기
            if participant is None:
                participant_mysql = await self.get_and_check_participant(self.participant_id, user) # mysql 연결
                if participant_mysql is not None:

                    participant = await self.save_participant_in_redis(participant_mysql)  # ✅ 캐싱 추가

            if participant is None:
                logging.info('participant not found or not match with user token')
                await self.send_json({'status': 400, 'error': '참가자 정보가 유효하지 않습니다.'})
                await self.close(code=400)
                return

            self.group_type = participant.group_type
            self.event_id = participant.event_id
            self.group_name = self.get_group_name(self.event_id, self.group_type)

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # 주기적으로 스코어를 전송하는 태스크를 설정
            self.send_task = asyncio.create_task(self.send_scores_periodically()) # 문제 없이 잘 됐음.
            await self.save_celery_event_from_redis_to_mysql(self.event_id) # 이벤트 자동 저장

        except ValueError as e:
            await self.close_with_status(500, str(e))

    async def disconnect(self, close_code):
        try:
            await self.decrease_event_auto_migration_count(self.event_id) # 이벤트 자동 저장 카운트 감소
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

            self.send_task.cancel()  # 주기적인 태스크 취소
        except Exception as e:
            logging.error(f'Error in disconnect: {e}')
            await self.close_with_status(500, str(e))

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        """
        클라이언트로부터 JSON 메시지 수신 및 분기 처리
        Supported actions:
        - get            : 전체 스코어 + 상태 조회
        - confirm_hole   : 홀 확정 (계산 + 상태 업데이트)
        - uncheck_hole   : 홀 수정 모드 전환 (상태 해제)
        - post           : 스코어 입력
        """
        # 1) JSON 파싱 에러 처리
        try:
            text_data_json = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json({
                'status': 400,
                'error': 'Invalid JSON format'
            })
            return

        action = text_data_json.get("action")
        hole_number = text_data_json.get("hole_number")
        participant_id = text_data_json.get("participant_id")

        # 2) 각 액션별 로직 실행 및 예외 처리
        try:
            # 수정 요청
            if action == 'uncheck_hole':
                await self.set_hole_check(self.event_id, self.group_type, hole_number, False)
                # 조 내 참여자 전체에게 데이터 전송
                await self.channel_layer.group_send(self.group_name, {
                    "type": "broadcast_scores"
                })
                return

            # 확인(계산) 요청
            elif action == 'confirm_hole':
                participant = await self.get_participant_from_redis(self.event_id, participant_id)
                if not participant:
                    await self.send_json({'status': 404, 'error': f'Participant {participant_id} not found'})
                    return

                await self.update_participant_sum_and_handicap_score_in_redis(participant)
                await self.update_rankings_in_redis(self.event_id)

                logging.info(f'isTeam? {participant.team_type != Participant.TeamType.NONE}')
                if participant.team_type != Participant.TeamType.NONE:
                    # 조별 승리 여부 갱신
                    await self.update_is_group_win_in_redis(participant)
                    # 전체 이벤트 승리 팀 갱신
                    await self.update_event_win_team_in_redis(self.event_id)

                # 확인 상태 저장
                await self.set_hole_check(self.event_id, self.group_type, hole_number, True)

                # 조 내 참여자 전체에게 데이터 전송
                await self.channel_layer.group_send(self.group_name, {
                    "type": "broadcast_scores"
                })
                return

            # 전체 스코어+상태 조회 요청
            elif action == 'get':
                await self.send_scores()
                return

            # 스코어 입력
            elif action == 'post': # TODO: input_score or update_score
                participant_id = text_data_json['participant_id']  # request body로 받는 참가자id
                hole_number = text_data_json['hole_number']
                score = text_data_json['score']

                participant: ParticipantRedisData = await self.get_participant_from_redis(event_id=self.event_id,
                                                                                          participant_id=participant_id)  # redis에서 참가자 정보 가져오기
                if (participant is None):
                    # 이미 저장된 참가자가 아닐 경우에만, 조회해서 캐싱
                    participant_mysql: Participant = await self.get_participant(participant_id)
                    if participant_mysql is None:
                        participant = None
                    else:
                        participant = await self.save_participant_in_redis(participant_mysql)  # ✅ 캐싱 추가

                if not participant:
                    await self.send_json(self.handle_404_not_found('Participant', participant_id))
                    return

                if hole_number is None:
                    await self.send_json({'status': 400, 'error': "Hole Number is required."})
                    return

                await self.update_hole_score_in_redis(participant_id, hole_number, score)

                participant = await self.get_participant_from_redis(event_id=self.event_id,
                                                                    participant_id=participant_id)  # redis에서 갱신된 참가자 정보 가져오기
                response_data_dict = asdict(participant)
                response_data_dict["hole_number"] = hole_number
                response_data_dict["score"] = score

                await self.channel_layer.group_send(self.group_name, {
                    'type': 'broadcast_scores',
                    **response_data_dict  # Send all response data
                })

                await self.save_celery_event_from_redis_to_mysql(self.event_id,
                                                                 is_count_incr=False)  # count 증가 없이, 자동 저장 시간 연장

                return
            else:
                # 알 수 없는 action 에 대한 에러 핸들
                await self.send_json({
                    'status': 400,
                    'error': f'Unknown action: {action}'
                })
                return

        except ValueError as e:
            await self.close_with_status(500, str(e))

    @staticmethod
    def get_group_name(event_id, group_type):
        return f"event_{event_id}_group_{group_type}_room"

    async def close_with_status(self, code, message):
        await self.send_json({'status': code, 'error': message})
        await self.close(code=code)

    def handle_404_not_found(self, model_name, pk):
        return {
            'status': 404,
            'error': f'{model_name} {pk} is not found'
        }

    async def broadcast_scores(self, event):
        """
        그룹에 broadcast_scores 메시지가 왔을 때 send_scores() 를 호출해 모두에게 최신 데이터 전송
        """
        await self.send_scores()
        try:
            await self.send_json(event)
        except Exception as e:
            await self.send_with_status(500, f'메시지 전송 실패, {e}')

    async def send_scores(self):
        """
        그룹 참가자의 실시간 점수 및 홀 확인 상태를 수집해 전송하는 함수
        - participants: Redis에서 그룹 필터링 후 가져온 ParticipantRedisData 리스트
        - hole_checks: 해당 그룹의 Redis hole_checks 해시
        """
        try:
            # 그룹에 속한 모든 참가자를 한 번의 쿼리로 가져옴
            participants = await self.get_group_participants_from_redis(self.event_id, self.group_type)
            logging.info(f'participants: {participants}')
            # 각 참가자의 홀 스코어를 비동기로 병렬 처리
            group_scores = await asyncio.gather(*[
                self.process_participant(participant) for participant in participants
            ])
            logging.info(f'group_scores: {group_scores}')

            hole_checks = await self.get_hole_checks(self.event_id, self.group_type)
            logging.info(f"hole_checks: {hole_checks}")
            await self.send_json({
                'scores': group_scores,
                'hole_checks': hole_checks,
            })
        except Exception as e:
            await self.send_with_status(500, f'스코어 기록을 가져오는 데 실패했습니다, {e}')

    async def process_participant(self, participant):
        participant_id = participant.participant_id
        hole_scores = await self.get_all_hole_scores_from_redis(participant_id)
        logging.info(f'hole_scores:{hole_scores}')
        return {
            'participant_id': participant_id,
            'user_name': participant.user_name,
            'group_type': participant.group_type,
            'team_type': participant.team_type,
            'is_group_win': participant.is_group_win,
            'is_group_win_handicap': participant.is_group_win_handicap,
            'sum_score': participant.sum_score,
            'handicap_score': participant.handicap_score,
            'scores': hole_scores,
        }

    async def send_json(self, content):
        # JSON 데이터를 WebSocket을 통해 전송

        try:
            logging.debug(f'Sending JSON: {content}')
            await self.send(text_data=json.dumps(content, ensure_ascii=False))
            logging.debug('JSON sent successfully')
        except Exception as e:
            logging.error(f'Error in send_json: {e}')
            await self.send_json({'status': 500, 'error': f'Error in send_json: {e}'})

    async def send_scores_periodically(self):
        # 주기적으로 참가자들의 점수를 전송

        while True:
            try:
                await self.send_scores()
            except Exception as e:
                await self.send_json({'status': 500, 'error': str(e)})
            await asyncio.sleep(300)  # 5분마다 주기적으로 스코어 전송