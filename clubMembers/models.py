'''
MVP demo ver 0.0.3
2024.07.11
ClubMember/models.py
'''
from django.db import models


# Create your models here.
class ClubMember(models.Model):
    club_member_name = models.CharField(max_length=25)
