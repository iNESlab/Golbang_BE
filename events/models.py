from datetime import datetime
from django.db import models
from members.models import Member


# Create your models here.
class Event(models.Model):
    class RepeatType(models.TextChoices):
        NONE = 'NONE', '반복 안함'
        EVERYDAY = 'DAY', '매일'
        EVERYWEEK = 'WEEK', '매주'
        EVERYMONTH = 'MONTH', '매월'
        EVERYYEAR = 'YEAR', '매년'

    class GameMode(models.TextChoices):
        MATCH_PLAY = 'MP', 'Match Play'
        STROKE_PLAY = 'SP', 'Stroke Play'

    # Todo: club 테이블 생성후 연결하기
    # club = models.ForeignKey(Club, on_delete=models)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    event_title = models.CharField("이벤트 제목", max_length=100, default='unknown_event')
    location = models.CharField("장소", max_length=255, default='unknown_location')
    start_date_time = models.DateTimeField("시작 시간", default=datetime.now)
    end_date_time = models.DateTimeField("종료 시간", default=datetime.now)
    repeat_type = models.CharField("반복 타입", max_length=5, choices=RepeatType.choices, default=RepeatType.NONE)
    game_mode = models.CharField("게임 모드", max_length=3, choices=GameMode.choices, default=GameMode.STROKE_PLAY)
    alert_date_time = models.DateTimeField("알람 일자", null=True, blank=True)
