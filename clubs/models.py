'''
MVP demo ver 0.0.3
2024.07.24
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

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES_TYPE, default='member')
    total_points = models.IntegerField(default=0)
    total_rank = models.CharField("모임 내 전체 랭킹", max_length=10, default="0", null=True, blank=True)
    total_handicap_rank = models.CharField("모임 내 전체 핸디캡 적용 랭킹", max_length=10, default="0", null=True, blank=True)

    class Meta:
        unique_together = ('user', 'club')

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
