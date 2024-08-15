'''
MVP demo ver 0.0.8
2024.08.02
events/utils.py

역할: events view의 공통 유틸 클래스
기능: queryset이나 validate 처리 등
'''
from datetime import datetime
from django.db.models import Sum

from participants.models import HoleScore
from .models import Event


class EventUtils:
    # 해당 달의 이벤트 리스트를 가져오는 쿼리
    @staticmethod
    def get_month_events_queryset(year, month, status_type, user):

        start_date = datetime(year, month, 1)
        next_month = month % 12 + 1
        next_month_year = year if month < 12 else year + 1
        end_date = datetime(next_month_year, next_month, 1)

        events = (Event.objects
                  .filter(participant__club_member__user=user,
                          start_date_time__gte=start_date,
                          start_date_time__lt=end_date)
                  .order_by('start_date_time'))

        if status_type is None:
            return events

        return events.filter(participant__status_type__in=['ACCEPT', 'PARTY'])

    @staticmethod
    def is_duplicated_participants(participants):
        member_ids = [participant['member_id'] for participant in participants]
        if len(member_ids) != len(set(member_ids)):
            return True
        return False

    @staticmethod
    def calculate_sum_score(participant):
        return HoleScore.objects.filter(participant=participant).aggregate(total=Sum('score'))['total']

    @staticmethod
    def calculate_handicap_score(participant):
        return int(participant.sum_score) - int(participant.club_member.user.handicap)

    @staticmethod
    def get_rank(participant):
        # EventResultSerializer에서 이미 rank가 계산되었으므로, 여기서는 그 값을 반환
        return participant.rank if participant.rank else None