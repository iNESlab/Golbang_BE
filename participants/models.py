'''
MVP demo ver 0.0.4
2024.08.27
participants/models.py

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
from django.db.models import Sum

from clubs.models import ClubMember
from events.models import Event


class Participant(models.Model):
    class TeamType(models.TextChoices):
        NONE = "NONE", "None" # 개인전인 경우 None
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
        PARTY = "PARTY", "수락 및 회식"
        ACCEPT = "ACCEPT", "수락"
        DENY = "DENY", "거절"
        PENDING = "PENDING", "대기"

    club_member     = models.ForeignKey(ClubMember, on_delete=models.CASCADE, null=False, blank=True)
    event           = models.ForeignKey(Event, on_delete=models.CASCADE, null=False, blank=True)
    team_type       = models.CharField("팀 타입", max_length=6, choices=TeamType.choices, default=TeamType.NONE)
    group_type      = models.IntegerField("조 타입", choices=GroupType.choices, null=False, blank=False)
    status_type     = models.CharField("상태", max_length=7, choices=StatusType.choices, default=StatusType.PENDING)
    sum_score       = models.IntegerField("총 점수", default=0) #TODO: 웹소켓으로 점수 입력할 때마다 갱신이 어려우면 제거.
    handicap_score  = models.IntegerField("핸디캡 점수", default=0) #TODO: 웹소켓으로 점수 입력할 때마다 갱신이 어려우면 제거.
    rank            = models.CharField("랭킹", max_length=10, default="0", null=True, blank=True) #TODO: 정렬 방법(sum_score or handicap_Score)에 따라 바뀌므로 없어도 될거 같음
    handicap_rank   = models.CharField("핸디캡 랭킹", max_length=10, default="0", null=True, blank=True)
    points          = models.IntegerField("포인트", default=0)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    # TODO: 향후, event랑 participant 중간에 group 테이블을 만들어서 각 조별 승리를 관리하는게 나을지도...
    is_group_win = models.BooleanField("속한 조에서 승리 여부", default=False)
    is_group_win_handicap = models.BooleanField("속한 조에서 핸디캡 승리 여부", default=False)

    def get_scorecard(self):
        """
        참가자의 1~18홀 점수를 반환하며, 누락된 점수는 None으로 채운다.
        """
        # MySQL의 participants_holescore 테이블에서 유저의 스코어카드를 가져오는 로직 (재사용성을 위해 모델에 정의함)
        hole_scores = HoleScore.objects.filter(participant=self).order_by('hole_number')

        # {hole_number: score} 형태로 매핑
        hole_score_map = {hole.hole_number: hole.score for hole in hole_scores}
        print(f"hole_score_map: {hole_score_map}")
        # 1~18홀 점수를 채우고, 누락된 점수는 None으로 채운다.
        complete_scorecard = [hole_score_map.get(hole, None) for hole in range(1, 19)]
        print(f"complete_scorecard: {complete_scorecard}")
        return complete_scorecard


    def get_front_nine_score(self): # 전반전 점수
        return HoleScore.objects.filter(participant=self, hole_number__lte=9).aggregate(total=Sum('score'))[
            'total'] or 0

    def get_back_nine_score(self): # 후반전 점수
        return HoleScore.objects.filter(participant=self, hole_number__gte=10).aggregate(total=Sum('score'))[
            'total'] or 0

    def get_total_score(self):
        return HoleScore.objects.filter(participant=self).aggregate(total=Sum('score'))['total'] or 0

    def get_handicap_score(self):
        return self.get_total_score() - self.club_member.user.handicap

    def has_complete_scorecard(self) -> bool:
        """
        1~18홀까지 모두 점수가 채워져 있는지 여부를 반환.
        하나라도 None이 있으면 False.
        """
        return None not in self.get_scorecard()

    def calculate_points(self):
        """
        참가자의 포인트를 계산하여 데이터베이스에 저장한다.
        포인트 = 스코어 점수 + 출석 점수
        스코어 점수는 참가자 순위에 따라 부여되고, 출석 시 기본적으로 2점을 추가로 제공한다.
        """

        # total_score와 handicap_score가 모두 0이면 함수를 종료
        if self.rank == '0' or self.handicap_rank == '0':
            return

        # 기본 출석 점수 (2점)
        attendance_points = 2

        # 참가자 수를 기준으로 스코어 점수를 계산 (참가자 수가 20명일 때 1등: 20점, 꼴등: 1점)
        total_participants = Participant.objects.filter(event=self.event).count()

        # 동점 처리와 관련된 랭크 처리
        score_points = 0
        if self.rank.startswith('T'):  # 동점자의 경우
            rank_value = int(self.rank[1:])  # 'T2' -> 2
        else:
            rank_value = int(self.rank)

        # 점수 계산: 동점자 수를 고려한 점수 할당
        score_points = total_participants - rank_value + 1

        # 총 포인트 계산
        total_points = attendance_points + score_points

        # 포인트 저장
        self.points = total_points
        self.save()
   
class HoleScore(models.Model):

    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, null=False, blank=False)
    hole_number = models.IntegerField("홀 번호", default=1)
    score = models.IntegerField("홀 점수", default=0)
