from django.shortcuts import render
from rest_framework import viewsets

from participants.models import Participant
from participants.serializers import ParticipantCreateSerializer


# Create your views here.
class ParticipantViewSet(viewsets.ModelViewSet):
    queryset = Participant.objects.all()
    serializer_class = ParticipantCreateSerializer
