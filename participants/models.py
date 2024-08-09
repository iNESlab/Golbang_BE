'''
MVP demo ver 0.0.3
2024.08.02
events/models.py

역할: 참가자(Participant)과 관련된 데이터베이스 모델을 정의
기능:
- 참가자 정보 저장 (조, 팀, 수락 상태, 총점, 랭킹, 생성일, 수정일)
- event, club_member와 각각 1:n관계

역할: 홀 점수(HoleScore)과 관련된 데이터베이스 모델을 정의
기능:
- 홀 점수 저장(홀 번호, 점수)
- participant와 1:n관계
'''
from django.db import models

from clubs.models import ClubMember
from events.models import Event


# Create your models here.
class Participant(models.Model):
    class TeamType(models.TextChoices):
        NONE = "NONE", "None"
        TEAM1 = "A", "Team A"
        TEAM2 = "B", "Team B"

    class GroupType(models.IntegerChoices):
        GROUP1 = 1, "1조"
        GROUP2 = 2, "2조"
        GROUP3 = 3, "3조"
        GROUP4 = 4, "4조"
        GROUP5 = 5, "5조"
        GROUP6 = 6, "6조"
        GROUP7 = 7, "7조"
        GROUP8 = 8, "8조"

    class StatusType(models.TextChoices):
        PARTY        = "PARTY", "수락 및 회식"
        ACCEPT       = "ACCEPT", "수락"
        DENY         = "DENY", "거절"
        PENDING      = "PENDING", "대기"

    club_member = models.ForeignKey(ClubMember, on_delete=models.CASCADE, null=False, blank=True)
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, null=False, blank=True)
    team_type   = models.CharField("팀 타입", max_length=6, choices=TeamType.choices, default=TeamType.NONE)
    group_type  = models.IntegerField("조 타입", choices=GroupType.choices, null=False, blank=False)
    status_type = models.CharField("상태", max_length=7, choices=StatusType.choices, default=StatusType.PENDING)
    sum_score   = models.IntegerField("총 점수", default=0) #TODO: 웹소켓으로 점수 입력할 때마다 갱신이 어려우면 제거.
    rank        = models.IntegerField("랭킹",default=0) #TODO: 정렬 방법(sum_score or handicap_Score)에 따라 바뀌므로 없어도 될거 같음
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class HoleScore(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, null=False, blank=False)
    hole_number = models.IntegerField("홀 번호", default=1)
    score       = models.IntegerField("홀 점수", default=0)