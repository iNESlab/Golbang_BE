from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import ClubMember
from .serializers import ClubMemberSerializer


class ClubMemberViewSet(viewsets.ModelViewSet):
    queryset = ClubMember.objects.all()
    serializer_class = ClubMemberSerializer
