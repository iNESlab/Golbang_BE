from channels.db import database_sync_to_async

from participants.models import Participant, HoleScore

class MySQLInterface:

    @database_sync_to_async
    def update_or_create_hole_score_in_db(self, participant_id, hole_number, score):
        return HoleScore.objects.update_or_create(
            participant_id=participant_id,
            hole_number=hole_number,
            defaults={'score': score}
        )

    @database_sync_to_async
    def update_participant_rank_in_db(self, participant_id, rank, handicap_rank, sum_score, handicap_score):
        Participant.objects.filter(id=participant_id).update(rank=rank, handicap_rank=handicap_rank,
                                                             sum_score=sum_score, handicap_score=handicap_score)

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
            participant = Participant.objects.select_related('club_member__user','event').get(id=participant_id)
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
