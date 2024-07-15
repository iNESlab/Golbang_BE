'''
MVP demo ver 0.0.2
2024.07.22
clubs/models.py

역할: 모임(Club)과 관련된 데이터베이스 모델을 정의
기능:
- 모임 정보 저장 (이름, 설명, 이미지 등)
- 멤버와 관리자 정보를 ManyToManyField로 관리
'''
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Club(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField()
    image       = models.ImageField(upload_to='clubs/')
    members     = models.ManyToManyField(User, related_name='clubs')        # 모임 멤버
    admins      = models.ManyToManyField(User, related_name='admin_clubs')  # 모임 관리자
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
