from django.db import models
from clubMembers.models import ClubMember
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
        ACCEPT = "ACCEPT", "수락"
        DENY = "DENY", "거절"
        PENDING = "PENDING", "대기"

    participant_id = models.BigAutoField(primary_key=True)
    club_member = models.ForeignKey(ClubMember, on_delete=models.CASCADE, null=False, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=False, blank=True)
    team_type = models.CharField("팀 타입", max_length=6, choices=TeamType.choices, default=TeamType.NONE)
    group_type = models.IntegerField("조 타입", choices=GroupType.choices, null=False, blank=False)
    handicap = models.IntegerField("핸디캡", default=0)
    status_type = models.CharField("상태", max_length=7, choices=StatusType.choices, default=StatusType.PENDING)
    sum_score = models.IntegerField("총 점수", default=0)
    rank = models.IntegerField("랭킹",default=0)
