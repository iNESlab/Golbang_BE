# Create your models here.
from django.db import models


# Create your models here.
class Member(models.Model):
    member_name = models.CharField(max_length=25)