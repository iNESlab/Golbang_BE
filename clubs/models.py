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

User = get_user_model()

class Club(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    image       = models.ImageField(upload_to='clubs/', null=True, blank=True)
    members     = models.ManyToManyField(User, through='ClubMember', related_name='clubs')
    admins      = models.ManyToManyField(User, related_name='admin_clubs')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ClubMember(models.Model):
    ROLE_CHOICES_TYPE = (
        ('member', 'Member'),
        ('admin', 'Admin'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES_TYPE, default='member')

    class Meta:
        unique_together = ('user', 'club')
