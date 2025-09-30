'''
MVP demo ver 0.0.9
2024.08.28
clubs/models.py

역할: 모임(Club)과 관련된 데이터베이스 모델을 정의
기능:
- 모임 정보 저장 (이름, 설명, 이미지 등)
- 멤버와 관리자 정보를 ManyToManyField로 관리
- 멤버의 역할 표시
'''
from django.db import models
from django.contrib.auth import get_user_model

from django.db.models import Sum

User = get_user_model()

import logging

logger = logging.getLogger(__name__)

class Club(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    image       = models.ImageField(upload_to='clubs/', null=True, blank=True)
    members = models.ManyToManyField(User, through='ClubMember', related_name='clubs')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ClubMember(models.Model):
    ROLE_CHOICES_TYPE = (
        ('member', 'M'),
        ('admin', 'A'),
    )
    STATUS_CHOICES_TYPE = (
        ('invited', '초대됨'),      # 관리자가 초대
        ('applied', '가입신청'),    # 사용자가 신청
        ('active', '활성'),        # 승인됨
        ('rejected', '거절됨'),     # 거절됨
        ('banned', '차단됨'),       # 차단됨
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES_TYPE, default='member')
    status_type = models.CharField(max_length=10, choices=STATUS_CHOICES_TYPE, default='active')
    total_points = models.IntegerField(default=0)
    total_rank = models.CharField("모임 내 전체 랭킹", max_length=10, default="0", null=True, blank=True)
    total_handicap_rank = models.CharField("모임 내 전체 핸디캡 적용 랭킹", max_length=10, default="0", null=True, blank=True)
    total_avg_score = models.FloatField("모임 내 모든 이벤트의 평균 점수", default=0.0)
    total_handicap_avg_score = models.FloatField("모임 내 모든 이벤트의 핸디캡 적용 평균 점수", default=0.0)

    class Meta:
        unique_together = ('user', 'club')

    # TODO: 아래 함수들의 위치를 models.py에 둘 지 아니면 따로 utils나 다른 파일을 만들어할 지 정하기
    def update_total_points(self):
        """
        클럽 멤버의 전체 포인트를 모든 이벤트의 포인트 합으로 업데이트
        """
        from participants.models import Participant

        # 참가자의 모든 이벤트 포인트를 합산
        total_points = Participant.objects.filter(club_member=self).aggregate(total=Sum('points'))['total'] or 0

        # 총 포인트 업데이트
        self.total_points = total_points
        self.save()

    @classmethod
    def calculate_avg_rank(cls, club):
        """
        클럽 멤버들의 평균 점수를 기준으로 랭킹을 계산하고 업데이트하는 함수
        """
        from participants.models import Participant

        # 1. 해당 클럽의 모든 멤버
        members = cls.objects.filter(club=club)

        # 2. 각 멤버의 평균 점수를 계산하고 업데이트
        for member in members:
            # 해당 멤버가 참여한 모든 이벤트에서의 총점(sum_score)을 합산
            total_sum_score = Participant.objects.filter(club_member=member).aggregate(
                total=Sum('sum_score'))['total'] or 0

            # 해당 멤버가 참여한 이벤트의 개수
            event_count = Participant.objects.filter(club_member=member).count()

            # 평균 점수를 계산하여 업데이트
            member.total_avg_score = total_sum_score / event_count if event_count > 0 else 0
            member.save()
            logger.info(f"=========================member {member.user.name}: {member.total_avg_score}========")

        # 3. 모든 멤버를 평균 점수 기준으로 정렬하여 랭킹을 부여
        sorted_members = sorted(members, key=lambda m: m.total_avg_score)
        cls.assign_ranks(sorted_members, 'total_avg_score')

    @classmethod
    def calculate_handicap_avg_rank(cls, club):
        """
        핸디캡 평균 점수를 기준으로 클럽 멤버들의 랭킹을 계산하고 업데이트하는 함수
        """
        from participants.models import Participant

        members = cls.objects.filter(club=club)

        # 2. 각 멤버의 핸디캡 평균 점수를 계산하고 업데이트
        for member in members:
            # 해당 멤버가 참여한 모든 이벤트에서의 핸디캡 점수(handicap_score)를 합산

            total_handicap_score = Participant.objects.filter(club_member=member).aggregate(
                total=Sum('handicap_score'))['total'] or 0

            # 해당 멤버가 참여한 이벤트의 개수
            event_count = Participant.objects.filter(club_member=member).count()

            # 핸디캡 평균 점수를 계산하여 업데이트
            member.total_handicap_avg_score = total_handicap_score / event_count if event_count > 0 else 0
            member.save()

        # 3. 모든 멤버를 핸디캡 평균 점수 기준으로 정렬하여 랭킹을 부여
        sorted_members = sorted(members, key=lambda m: m.total_handicap_avg_score)
        cls.assign_ranks(sorted_members, 'total_handicap_avg_score')

    def assign_ranks(members, type):
        """
        동점자를 고려한 순위를 계산하여 데이터베이스에 저장.
        type이 'total_avg_score'일 경우 'total_rank'에, 'total_handicap_avg_score'일 경우 'total_handicap_rank'에 순위 저장.
        """
        previous_score = None
        rank = 1
        tied_rank = 1  # 동점자의 랭크를 별도로 관리

        # type 설정: type에 따라 업데이트할 필드를 동적으로 결정
        rank_field = 'total_rank' if type == 'total_avg_score' else 'total_handicap_rank'

        for idx, member in enumerate(members):
            current_score = getattr(member, type)

            if current_score == previous_score:
                setattr(member, rank_field, f"T{tied_rank}")  # 이전 참가자와 동일한 점수라면 T로 표기
                setattr(members[idx - 1], rank_field, f"T{tied_rank}")  # 이전 참가자의 랭크도 T로 업데이트
            else:
                setattr(member, rank_field, str(rank))  # 새로운 점수일 경우 일반 순위
                tied_rank = rank  # 새로운 점수에서 동점 시작 지점을 설정

            previous_score = current_score
            rank += 1  # 다음 순위로 이동

            # 업데이트된 랭킹을 데이터베이스에 저장
            member.save()