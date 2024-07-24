'''
MVP demo ver 0.0.3
2024.07.11
ClubMember/models.py
'''
from django.db import models

from members.models import Member

# Create your models here.
class ClubMember(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, null=False, blank=True)
