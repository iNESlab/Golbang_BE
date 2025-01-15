'''
MVP demo ver 0.0.3
2024.08.23
participa/stroke/mysql_interface.py

- MySQL 데이터베이스와 상호작용하는 클래스
- 참가자와 이벤트의 데이터를 관리함
'''
import asyncio # 비동기 작업
import logging
from dataclasses import asdict

from sympy import Q

from asgiref.sync import sync_to_async # 비동기 작업을 동기 함수로 전환하기 위한 함수
from channels.db import database_sync_to_async # 데이터베이스 작업을 비동기 함수로 전환하기 위한 함수

from events.models import Event
from participants.models import Participant, HoleScore
from participants.stroke.data_class import ParticipantUpdateData, EventData
from participants.stroke.redis_interface import redis_client


class MySQLInterface:

    @database_sync_to_async
    def update_or_create_hole_score_in_db(self, participant_id, hole_number, score):
        return HoleScore.objects.update_or_create(
            participant_id=participant_id,
            hole_number=hole_number,
            defaults={'score': score}
        )

    @database_sync_to_async
    def update_participant_rank_in_db(self, participant_id, participant_data):
        Participant.objects.filter(id=participant_id).update(**asdict(participant_data))

    @database_sync_to_async
    def get_group_participants(self, event_id, group_type=None):
        # 특정 이벤트와 그룹 타입에 해당하는 참가자들을 반환
        if group_type is None:
            raise ValueError("Group type is missing")
        return list(Participant.objects
                    .filter(event_id=event_id, group_type=group_type)
                    .select_related('club_member__user'))

    @database_sync_to_async
    def get_event_participants(self, event_id):
        # 특정 이벤트에 참여한 모든 참가자를 반환
        return list(Participant.objects.filter(
            Q(status_type=Participant.StatusType.PARTY) | Q(status_type=Participant.StatusType.ACCEPT),
            event_id=event_id
        ).select_related('club_member__user'))

    @database_sync_to_async
    def get_and_check_participant(self, participant_id, user):
        # 주어진 참가자 ID와 일치하는 참가자 정보를 가져오고, 해당 사용자인지 확인
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
            return Participant.objects.select_related('club_member__user', 'event').get(id=participant_id)
        except Participant.DoesNotExist:
            return None

    # 원래는 redis를 그대로 저장하면 되는데, 너무 길어져서 그냥 event 모델의 method 이용
    async def determine_and_update_win_status(self, participant, event):
        # 한 참가자를 기준으로 조별 및 전체 승리 팀을 결정하고 업데이트
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

    @database_sync_to_async
    def update_event_data_in_db(self, event_id, event_data):
        # 이벤트 데이터 업데이트
        Event.objects.filter(id=event_id).update(**asdict(event_data))

    async def transfer_participant_data_to_db(self, event_id, participants):
        from clubs.models import ClubMember
        try:
            # Redis에서 참가자 데이터를 가져와서 MySQL로 전달
            for participant in participants:
                redis_key = f'event:{event_id}:participant:{participant.id}'
                logging.info('redis_key: %s', redis_key)

                participant_data_dict = await sync_to_async(redis_client.hgetall)(redis_key)
                logging.info('participant_data_dict: %s', participant_data_dict)

                # ParticipantUpdateData 객체 생성
                participant_data = ParticipantUpdateData(
                    rank=participant_data_dict.get(b"rank"),
                    handicap_rank=participant_data_dict.get(b"handicap_rank"),
                    sum_score=participant_data_dict.get(b"sum_score"),
                    handicap_score=participant_data_dict.get(b"handicap_score"),
                    is_group_win=participant_data_dict.get(b"is_group_win"),
                    is_group_win_handicap=participant_data_dict.get(b"is_group_win_handicap")
                )

                if participant_data.rank is not None and participant_data.handicap_rank is not None:
                    await self.update_participant_rank_in_db(participant.id, participant_data)

                # 참가자 포인트 계산 및 저장
                await sync_to_async(participant.calculate_points)()

        except Exception as e:
            logging.error(f"Error updating participant data: {e}")

        # 모든 참가자의 포인트 계산이 끝난 후, 클럽 멤버들의 총 포인트 업데이트
        try:
            club = participants[0].event.club  # 첫 번째 참가자가 속한 모임을 가져옴 (모든 참가자가 동일한 클럽에 속해있음)
            for member in ClubMember.objects.filter(club=club):
                await sync_to_async(member.update_total_points)()

            # 클럽 멤버들의 평균 점수 및 핸디캡 점수 랭킹 업데이트
            await sync_to_async(ClubMember.calculate_avg_rank)(club)
            await sync_to_async(ClubMember.calculate_handicap_avg_rank)(club)

        except Exception as e:
            logging.error(f"Error updating club member points or ranks: {e}")

    async def transfer_hole_scores_to_db(self, participants):
        # Redis에서 홀 점수를 가져와서 MySQL로 전달
        for participant in participants:
            score_keys_pattern = f'participant:{participant.id}:hole:*'
            score_keys = await sync_to_async(redis_client.keys)(score_keys_pattern)
            logging.info('score_keys: %s', score_keys)

            async def update_or_create_hole_score(key):
                hole_number = int(key.decode('utf-8').split(':')[-1])
                score = int(await sync_to_async(redis_client.get)(key))
                await self.update_or_create_hole_score_in_db(participant.id, hole_number, score)

            await asyncio.gather(*(update_or_create_hole_score(key) for key in score_keys))

    async def transfer_event_data_to_db(self, event_id):
        # Redis에서 이벤트 데이터를 가져와서 MySQL로 전달
        event_key = f'event:{event_id}'
        event_data_dict = await sync_to_async(redis_client.hgetall)(event_key)

        # EventData 객체 생성
        event_data = EventData(
            group_win_team=event_data_dict.get(b"group_win_team"),
            group_win_team_handicap=event_data_dict.get(b"group_win_team_handicap"),
            total_win_team=event_data_dict.get(b"total_win_team"),
            total_win_team_handicap=event_data_dict.get(b"total_win_team_handicap")
        )

        await self.update_event_data_in_db(event_id, event_data)
