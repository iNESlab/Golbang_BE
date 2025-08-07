'''
MVP demo ver 0.0.3
2024.08.23
participa/stroke/mysql_interface.py

- MySQL 데이터베이스와 상호작용하는 클래스
- 참가자와 이벤트의 데이터를 관리함
'''
import logging
from dataclasses import asdict

from sympy import Q

from channels.db import database_sync_to_async # 데이터베이스 작업을 비동기 함수로 전환하기 위한 함수

from events.models import Event
from participants.models import Participant, HoleScore

class MySQLInterface:

    @database_sync_to_async
    def get_group_participants(self, event_id, group_type=None):
        # 특정 이벤트와 그룹 타입에 해당하는 참가자들을 반환
        if group_type is None:
            raise ValueError("Group type is missing")
        return list(Participant.objects
                    .filter(event_id=event_id, group_type=group_type)
                    .select_related('club_member__user'))

    # @database_sync_to_async
    # def get_event_participants(self, event_id):
    #     # 특정 이벤트에 참여한 모든 참가자를 반환
    #     return list(Participant.objects.filter(event_id=event_id).select_related('club_member__user'))

    @database_sync_to_async
    def get_and_check_participant(self, participant_id, user):
        # 주어진 참가자 ID와 일치하는 참가자 정보를 가져오고, 해당 사용자인지 확인
        try:
            participant = Participant.objects.select_related('club_member__user', 'event').get(id=participant_id)
            logging.info('participant: %s', participant.club_member.user.name)
            logging.info('user: %s', user.name)
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

    # # 원래는 redis를 그대로 저장하면 되는데, 너무 길어져서 그냥 event 모델의 method 이용
    # async def determine_and_update_win_status(self, participant, event):
    #     # 한 참가자를 기준으로 조별 및 전체 승리 팀을 결정하고 업데이트
    #     # participant: 한 조의 한 참가자를 의미 (한명 바꿔도 같은 조의 모든 인원이 갱신되기 때문)
    #     if not participant:
    #         logging.warning('No participants found for event_id: %s', event.id)
    #         return

    #     # 조별 승리 여부 갱신
    #     participant.determine_is_group_win()
    #     participant.determine_is_group_win_handicap()

    #     # 이벤트 전체 승리팀 결정
    #     event.determine_group_win_team()
    #     event.determine_group_win_team_handicap()
    #     event.determine_total_win_team()
    #     event.determine_total_win_team_handicap()

    #     # 최종적으로 데이터베이스에 저장
    #     await sync_to_async(participant.save)()
    #     await sync_to_async(event.save)()

    

