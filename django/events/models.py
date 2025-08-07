'''
MVP demo ver 0.0.4
2024.08.27
events/models.py

역할: 이벤트(Event)과 관련된 데이터베이스 모델을 정의
기능:
- 이벤트 정보 저장 (제목, 장소, 시작-끝 시간, 반복, 게임 모드, 알람 시간, 생성일, 수정일)
- club 과 1: n 관계로 정의
'''
from datetime import datetime
from django.db import models
from django.db.models import Sum

from clubs.models import Club, ClubMember
from golf_data.models import GolfClub, GolfCourse


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

    club            = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='events') # related_name: 역참조
    event_title     = models.CharField("이벤트 제목", max_length=100, default='unknown_event')
    location        = models.CharField("위도/경도", max_length=255, default='unknown_location')
    site            = models.CharField("장소명", max_length=255, default='unknown_site') # TODO: 모두 이관한 후 삭제 필요
    golf_club       = models.ForeignKey(GolfClub, on_delete=models.PROTECT, related_name='events', verbose_name="골프장", null=True, blank=True)
    golf_course     = models.ForeignKey(GolfCourse, on_delete=models.PROTECT, related_name='events', verbose_name="골프 코스", null=True, blank=True)
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

    def calculate_group_scores(self):
        from participants.models import Participant  # 지연 import
        """
        각 조별로 팀 A와 팀 B의 점수를 합산하여 전체 조별 점수를 계산한다.
        """
        participants = Participant.objects.filter(event=self)
        group_scores = participants.values('group_type').distinct()  # 각 조의 그룹 타입을 중복 없이 가져온다.

        # 각 팀의 조별 승리 횟수를 카운트하기 위한 변수 초기화
        a_group_wins = 0
        b_group_wins = 0

        # 각 그룹 타입에 대해 반복하면서 A팀과 B팀의 총점을 각각 계산한다.
        for group in group_scores:
            group_type = group['group_type']
            # 각 팀의 점수를 합산한다. 만약 점수가 None(없음)일 경우 0으로 설정
            team_a_score = participants.filter(group_type=group_type, team_type=Participant.TeamType.TEAM1).aggregate(
                total=Sum('sum_score'))['total'] or 0
            team_b_score = participants.filter(group_type=group_type, team_type=Participant.TeamType.TEAM2).aggregate(
                total=Sum('sum_score'))['total'] or 0

            # 각 팀의 점수를 비교하여 더 높은 점수를 가진 팀의 승리 횟수를 증가시킨다.
            if team_a_score < team_b_score:
                b_group_wins += 1
            elif team_b_score < team_a_score:
                a_group_wins += 1

        # 각 팀의 조별 승리 횟수를 이벤트의 관련 필드에 저장한다.
        self.team_a_group_wins = a_group_wins
        self.team_b_group_wins = b_group_wins

        # 조별 승리 횟수를 비교하여 전체 조별 승리 팀을 결정하고 저장한다.
        if a_group_wins > b_group_wins:
            self.group_win_team = self.WinningTeamType.TEAM1
        elif b_group_wins > a_group_wins:
            self.group_win_team = self.WinningTeamType.TEAM2
        else:
            self.group_win_team = self.WinningTeamType.DRAW

        self.save() # 변경된 데이터를 데이터베이스에 저장

    def calculate_total_scores(self):
        from participants.models import Participant  # 지연 import
        """
        모든 조의 점수를 합산하여 팀 A와 팀 B의 전체 점수를 계산한다.
        """
        participants = Participant.objects.filter(event=self)
        # 각 팀의 전체 점수를 합산하여 필드에 저장한다. 합계가 None일 경우 0으로 설정한다.
        self.team_a_total_score = \
        participants.filter(team_type=Participant.TeamType.TEAM1).aggregate(total=Sum('sum_score'))['total'] or 0
        self.team_b_total_score = \
        participants.filter(team_type=Participant.TeamType.TEAM2).aggregate(total=Sum('sum_score'))['total'] or 0

        # 전체 점수를 비교하여 더 낮은 점수를 가진 팀을 승리 팀으로 설정한다.
        if self.team_a_total_score < self.team_b_total_score:
            self.total_win_team = self.WinningTeamType.TEAM1
        elif self.team_b_total_score < self.team_a_total_score:
            self.total_win_team = self.WinningTeamType.TEAM2
        else:
            self.total_win_team = self.WinningTeamType.DRAW

        self.save() # 변경된 데이터를 데이터베이스에 저장

    # 팀전 핸디캡 결과 계산 로직
    def calculate_group_scores_with_handicap(self):
        from participants.models import Participant  # 지연 import

        """
        각 조별로 팀 A와 팀 B의 핸디캡 적용 점수를 합산하여 전체 조별 점수를 계산한다.
        """
        participants = Participant.objects.filter(event=self)
        group_scores = participants.values('group_type').distinct()

        a_group_wins_handicap = 0
        b_group_wins_handicap = 0

        for group in group_scores:
            group_type = group['group_type']
            team_a_score_handicap = \
            participants.filter(group_type=group_type, team_type=Participant.TeamType.TEAM1).aggregate(
                total=Sum('handicap_score'))['total'] or 0
            team_b_score_handicap = \
            participants.filter(group_type=group_type, team_type=Participant.TeamType.TEAM2).aggregate(
                total=Sum('handicap_score'))['total'] or 0

            if team_a_score_handicap < team_b_score_handicap:
                b_group_wins_handicap += 1
            elif team_b_score_handicap < team_a_score_handicap:
                a_group_wins_handicap += 1

        self.team_a_group_score_handicap = a_group_wins_handicap
        self.team_b_group_score_handicap = b_group_wins_handicap

        if a_group_wins_handicap > b_group_wins_handicap:
            self.group_win_team_handicap = self.WinningTeamType.TEAM1
        elif b_group_wins_handicap > a_group_wins_handicap:
            self.group_win_team_handicap = self.WinningTeamType.TEAM2
        else:
            self.group_win_team_handicap = self.WinningTeamType.DRAW

        self.save()

    def calculate_total_scores_with_handicap(self):
        from participants.models import Participant  # 지연 import

        """
        모든 조의 핸디캡 적용 점수를 합산하여 팀 A와 팀 B의 전체 점수를 계산한다.
        """
        participants = Participant.objects.filter(event=self)
        self.team_a_total_score_handicap = \
        participants.filter(team_type=Participant.TeamType.TEAM1).aggregate(total=Sum('handicap_score'))[
            'total'] or 0
        self.team_b_total_score_handicap = \
        participants.filter(team_type=Participant.TeamType.TEAM2).aggregate(total=Sum('handicap_score'))[
            'total'] or 0

        if self.team_a_total_score_handicap < self.team_b_total_score_handicap:
            self.total_win_team_handicap = self.WinningTeamType.TEAM2
        elif self.team_b_total_score_handicap < self.team_a_total_score_handicap:
            self.total_win_team_handicap = self.WinningTeamType.TEAM1
        else:
            self.total_win_team_handicap = self.WinningTeamType.DRAW

        self.save()