import asyncio
import logging
from dataclasses import dataclass

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async

from participants.models import Participant, HoleScore
from participants.team_socket.redis_interface import redis_client


@dataclass
class ParticipantData:
    participant_id: int
    rank: str
    handicap_rank: str
    sum_score: int
    handicap_score: int
    is_group_win: bool
    is_group_win_handicap: bool


class MySQLInterface:

    @database_sync_to_async
    def update_or_create_hole_score_in_db(self, participant_id, hole_number, score):
        return HoleScore.objects.update_or_create(
            participant_id=participant_id,
            hole_number=hole_number,
            defaults={'score': score}
        )

    @database_sync_to_async
    def update_participant_rank_in_db(self, participant_data):
        Participant.objects.filter(id=participant_data.participant_id).update(rank=participant_data.rank,
                                                                              handicap_rank=participant_data.handicap_rank,
                                                                              sum_score=participant_data.sum_score,
                                                                              handicap_score=participant_data.handicap_score)

    @database_sync_to_async
    def get_group_participants(self, event_id, group_type=None):
        if group_type is None:
            raise ValueError("Group type is missing")
        return list(Participant.objects
                    .filter(event_id=event_id, group_type=group_type)
                    .select_related('club_member__user'))

    @database_sync_to_async
    def get_event_participants(self, event_id):
        return list(Participant.objects.filter(event_id=event_id).select_related('club_member__user'))

    @database_sync_to_async
    def get_and_check_participant(self, participant_id, user):
        try:
            participant = Participant.objects.select_related('club_member__user', 'event').get(id=participant_id)
            if participant.club_member.user != user:
                return None
            return participant
        except Participant.DoesNotExist:
            return None

    @database_sync_to_async
    def get_participant(self, participant_id):
        try:
            return Participant.objects.select_related('club_member__user','event').get(id=participant_id)
        except Participant.DoesNotExist:
            return None

    # 원래는 redis를 그대로 저장하면 되는데, 너무 길어져서 그냥 event 모델의 method 이용
    async def determine_and_update_win_status(self, participant, event):
        # participant: 한 조의 한 참가자를 의미 (한명 바꿔도 같은 조의 모든 인원이 갱신되기 때문)
        if not participant:
            logging.warning('No participants found for event_id: %s', event.id)
            return

        # 조별 승리 여부 갱신
        participant.determine_is_group_win()
        participant.determine_is_group_win_handicap()

        # 이벤트 전체 승리팀 결정
        event.determine_group_win_team()
        event.determine_group_win_team_handicap()
        event.determine_total_win_team()
        event.determine_total_win_team_handicap()

        # 최종적으로 데이터베이스에 저장
        await sync_to_async(participant.save)()
        await sync_to_async(event.save)()

    async def transfer_game_data_to_db(self):
        participants = await self.get_event_participants(self.event_id)
        for participant in participants:
            # 전체 참가자들의 랭킹 정보를 업데이트
            redis_key = f'participant:{participant.id}'
            logging.info('redis_key: %s', redis_key)
            rank = await sync_to_async(redis_client.hget)(redis_key, "rank")
            handicap_rank = await sync_to_async(redis_client.hget)(redis_key, "handicap_rank")
            sum_score = await sync_to_async(redis_client.hget)(redis_key, "sum_score")
            handicap_score = await sync_to_async(redis_client.hget)(redis_key, "handicap_score")
            is_group_win = await sync_to_async(redis_client.hget)(redis_key, "is_group_win")
            is_group_win_handicap = await sync_to_async(redis_client.hget)(redis_key, "is_group_win_handicap")

            # 가져온 데이터를 문자열로 변환
            participant_data = ParticipantData(
                participant_id=participant.id,
                rank=rank.decode('utf-8') if rank else None,
                handicap_rank=handicap_rank.decode('utf-8') if handicap_rank else None,
                sum_score=sum_score.decode('utf-8') if sum_score else None,
                handicap_score=handicap_score.decode('utf-8') if handicap_score else None,
                is_group_win=is_group_win.decode('utf-8') if is_group_win else None,
                is_group_win_handicap=is_group_win_handicap.decode('utf-8') if is_group_win_handicap else None
            )

            if rank is not None and handicap_rank is not None:
                # MySQL에 rank와 handicap_rank 업데이트
                await self.update_participant_rank_in_db(participant_data)

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
