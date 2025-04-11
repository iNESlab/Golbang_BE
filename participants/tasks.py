from dataclasses import asdict
import logging
import time

from django.db import transaction
from celery import shared_task
# from participants.stroke.mysql_interface import MySQLInterfaceSync
from events.models import Event
from participants.models import HoleScore, Participant
from participants.stroke.data_class import EventData, ParticipantUpdateData
from participants.stroke.redis_interface import redis_client


@shared_task
def save_event_periodically_task(event_id: int):

    print(f"event:[{event_id}] migrate start")

    mysql_client = MigrationMySQLInterface()
    key = f"event:{event_id}:is_saving"
    while True:
        try:
            with transaction.atomic():
                participants = mysql_client.get_event_participants(event_id)
                mysql_client.transfer_participant_data_to_db(event_id, participants)
                mysql_client.transfer_hole_scores_to_db(participants)
                mysql_client.transfer_event_data_to_db(event_id)
            print(f"event:[{event_id}] 저장 완료")

        except Exception as e:
            print(f"event[{event_id}] 저장 실패: {e}")

        print("test1")
        exists = redis_client.exists(key)
        print(f"[{event_id}] is_saving 키 존재 여부: {exists}")
        if not exists:
            print(f"[{event_id}] is_saving 키 없음 → 저장 종료")
            break

        count = redis_client.get(key)
        print(f"[{event_id}] 참가자 수: {count}")
        if count is not None and int(count) <= 0:
            print(f"[{event_id}] 참가자 0명 → 저장 종료")
            redis_client.delete(key)
            break

        time.sleep(30)


class MigrationMySQLInterface:
        def get_event_participants(self, event_id):
        # 특정 이벤트에 참여한 모든 참가자를 반환
            return list(Participant.objects.filter(event_id=event_id))
        
        def transfer_participant_data_to_db(self, event_id, participants):
            from clubs.models import ClubMember
            try:
                print('transfer_participant_data_to_db 실행')
                # Redis에서 참가자 데이터를 가져와서 MySQL로 전달
                for participant in participants:
                    redis_key = f'event:{event_id}:participant:{participant.pk}'
                    logging.info('redis_key: %s', redis_key)

                    participant_data_dict = redis_client.hgetall(redis_key)
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
                        self.update_participant_rank_in_db(participant.pk, participant_data)

                    # 참가자 포인트 계산 및 저장
                    participant.calculate_points()
                    print(f"Participant ID: {participant.pk}, Rank: {participant.rank}, Handicap Rank: {participant.handicap_rank}")

            except Exception as e:
                logging.error(f"Error updating participant data: {e}")

            # 모든 참가자의 포인트 계산이 끝난 후, 클럽 멤버들의 총 포인트 업데이트
            try:
                club = participants[0].event.club  # 첫 번째 참가자가 속한 모임을 가져옴 (모든 참가자가 동일한 클럽에 속해있음)
                for member in ClubMember.objects.filter(club=club):
                    member.update_total_points()

                    # 클럽 멤버들의 평균 점수 및 핸디캡 점수 랭킹 업데이트
                    ClubMember.calculate_avg_rank(club)
                    ClubMember.calculate_handicap_avg_rank(club)

            except Exception as e:
                logging.error(f"Error updating club member points or ranks: {e}")

        def transfer_hole_scores_to_db(self, participants):
            print('transfer_hole_Scores_to_db 실행')
            # Redis에서 홀 점수를 가져와서 MySQL로 전달
            for participant in participants:
                score_keys_pattern = f'participant:{participant.pk}:hole:*'
                score_keys = redis_client.keys(score_keys_pattern)
                logging.info('score_keys: %s', score_keys)

                for key in score_keys:
                    hole_number = int(key.decode('utf-8').split(':')[-1])
                    score = int(redis_client.get(key))  # ✅ 동기 호출
                    self.update_or_create_hole_score_in_db(participant.pk, hole_number, score)
            print('transfer_hole_Scores_to_db 실행종료')

        def transfer_event_data_to_db(self, event_id):
            print('transfer_event_data_to_db 실행')
            # Redis에서 이벤트 데이터를 가져와서 MySQL로 전달
            event_key = f'event:{event_id}'

            if(not redis_client.exists(event_key)):
                print(f"event:{event_id} 키가 존재하지 않습니다. 팀 게임이 아닙니다.")
                return
            
            event_data_dict = redis_client.hgetall(event_key)

            # EventData 객체 생성
            event_data = EventData(
                group_win_team=event_data_dict.get(b"group_win_team"),
                group_win_team_handicap=event_data_dict.get(b"group_win_team_handicap"),
                total_win_team=event_data_dict.get(b"total_win_team"),
                total_win_team_handicap=event_data_dict.get(b"total_win_team_handicap")
            )

            self.update_event_data_in_db(event_id, event_data)
            print('transfer_event_data_to_db 실행종료')

        def update_participant_rank_in_db(self, participant_id, participant_data):
            Participant.objects.filter(id=participant_id).update(**asdict(participant_data))
        
        def update_event_data_in_db(self, event_id, event_data):
        # 이벤트 데이터 업데이트
            Event.objects.filter(id=event_id).update(**asdict(event_data))

        def update_or_create_hole_score_in_db(self, participant_id, hole_number, score):
            return HoleScore.objects.update_or_create(
                participant_id=participant_id,
                hole_number=hole_number,
                defaults={'score': score}
            )