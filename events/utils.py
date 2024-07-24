from datetime import datetime, date
from django.utils import timezone

from .models import Event


class EventUtils:
    # 해당 달의 이벤트 리스트를 가져오는 쿼리
    @staticmethod
    def get_month_events_queryset(request, member):
        date_str = request.query_params.get('date')

        if not date_str:
            date_str = str(date.today())

        try:
            # 날짜 문자열을 파싱하여 datetime 객체로 변환
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
        except ValueError:
            return Event.objects.none()  # 빈 쿼리셋 반환

        start_date = datetime(year, month, 1)
        next_month = month % 12 + 1
        next_month_year = year if month < 12 else year + 1
        end_date = datetime(next_month_year, next_month, 1)

        return (Event.objects
                .filter(participant__club_member__member=member, start_date_time__gte=start_date, start_date_time__lt=end_date)
                .order_by('start_date_time'))
    # Month와 무관하게 곧 임박한 이벤트 20개 반환
    @staticmethod
    def get_upcoming_events(status_type, member):

        # 현재 날짜를 aware datetime으로 변환
        today = timezone.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_start_aware = timezone.make_aware(today_start)

        # Event 객체를 Member로 역참조하여 필터링
        events_by_member = Event.objects.filter(participant__club_member__member=member,
                                                start_date_time__gte=today_start_aware)

        # state_type이 제공되지 않은 경우, 기본적으로 필터링된 이벤트 목록을 반환
        if not status_type:
            return events_by_member.order_by('start_date_time')[:20]

        # state_type에 따라 추가 필터링
        return (events_by_member
                .filter(participant__status_type__in=['ACCEPT', 'PARTY'])
                .order_by('start_date_time')[:20])
