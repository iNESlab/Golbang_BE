'''
MVP demo ver 0.0.3
2024.07.11
ClubMember/models.py
'''
from django.db import models

from accounts.models import User


# Create your models here.
class ClubMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, blank=True)
