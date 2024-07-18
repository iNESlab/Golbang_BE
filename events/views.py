# events/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from clubMembers.models import ClubMember
from .models import Event
from .serializers import EventCreateSerializer, EventDetailSerializer


class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return EventDetailSerializer
        elif self.action == 'create':
            return EventCreateSerializer
        return EventCreateSerializer

    def create(self, request, *args, **kwargs):
        club_member_id = self.request.query_params.get('club_member_id')

        if not club_member_id:
            return Response({"detail": "club_member_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            club_member = ClubMember.objects.get(pk=club_member_id)
        except ClubMember.DoesNotExist:
            return Response({"detail": "Invalid club_member_id"}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()
        data['club_member_id'] = club_member.pk
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Use the same serializer for response to include all data
        return Response(serializer.data, status=status.HTTP_201_CREATED)