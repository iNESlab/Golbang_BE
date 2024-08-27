'''
MVP demo ver 0.0.3
2024.08.02
events/models.py

역할: 이벤트(Event)과 관련된 데이터베이스 모델을 정의
기능:
- 이벤트 정보 저장 (제목, 장소, 시작-끝 시간, 반복, 게임 모드, 알람 시간, 생성일, 수정일)
- club 과 1: n 관계로 정의
'''
from datetime import datetime
from django.db import models

from clubs.models import Club, ClubMember

# Create your models here.
class Event(models.Model):
    class RepeatType(models.TextChoices):
        NONE       = 'NONE', '반복 안함'
        EVERYDAY   = 'DAY', '매일'
        EVERYWEEK  = 'WEEK', '매주'
        EVERYMONTH = 'MONTH', '매월'
        EVERYYEAR  = 'YEAR', '매년'

    class GameMode(models.TextChoices):
        MATCH_PLAY  = 'MP', 'Match Play'
        STROKE_PLAY = 'SP', 'Stroke Play'

    class WinningTeamType(models.TextChoices):
        NONE = "NONE", "결과 없음"
        TEAM1 = "A", "Team A"
        TEAM2 = "B", "Team B"
        DRAW = "DRAW", "무승부"

    club            = models.ForeignKey(Club, on_delete=models.CASCADE)
    event_title     = models.CharField("이벤트 제목", max_length=100, default='unknown_event')
    location        = models.CharField("장소", max_length=255, default='unknown_location')
    start_date_time = models.DateTimeField("시작 시간", default=datetime.now)
    end_date_time   = models.DateTimeField("종료 시간", default=datetime.now)
    repeat_type     = models.CharField("반복 타입", max_length=5, choices=RepeatType.choices, default=RepeatType.NONE)
    game_mode       = models.CharField("게임 모드", max_length=3, choices=GameMode.choices, default=GameMode.STROKE_PLAY)
    alert_date_time = models.DateTimeField("알람 일자", null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 팀별 조별 승리 수
    team_a_group_wins = models.IntegerField("Team A 조별 승리 수", default=0)
    team_b_group_wins = models.IntegerField("Team B 조별 승리 수", default=0)
    team_a_group_wins_handicap = models.IntegerField("Team A 핸디캡 적용한 조별 승리 수", default=0)
    team_b_group_wins_handicap = models.IntegerField("Team B 핸디캡 적용한 조별 승리 수", default=0)

    # 팀별 전체 점수
    team_a_total_score = models.IntegerField("Team A 전체 점수 합계", default=0)
    team_b_total_score = models.IntegerField("Team B 전체 점수 합계", default=0)
    team_a_total_score_handicap = models.IntegerField("Team A 핸디캡 적용한 전체 점수 합계", default=0)
    team_b_total_score_handicap = models.IntegerField("Team B 핸디캡 적용한 전체 점수 합계", default=0)

    # 이벤트 최종 승리 팀
    ## 조별로 많이 이긴 팀을 승리팀으로 저장
    group_win_team          = models.CharField("승리 팀 by 조", max_length=4,
                                       choices=WinningTeamType.choices, default=WinningTeamType.NONE)
    ## 전체 스코어 합계를 토대로 승리팀 저장
    total_win_team          = models.CharField("승리 팀 by 합계", max_length=4,
                                       choices=WinningTeamType.choices, default=WinningTeamType.NONE)
    ## 핸디캡을 적용했을 때 조별로 많이 이긴 팀을 승리팀으로 저장
    group_win_team_handicap = models.CharField("승리 팀 by 핸디캡 조", max_length=4,
                                       choices=WinningTeamType.choices, default=WinningTeamType.NONE)
    ## 핸디캡을 적용하여 전체 스코어 합계를 토대로 승리팀 저장
    total_win_team_handicap = models.CharField("승리 팀 by 핸디캡 합계", max_length=4,
                                       choices=WinningTeamType.choices, default=WinningTeamType.NONE)
