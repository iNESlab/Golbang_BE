'''
MVP demo ver 0.0.1
2024.07.15
participants/serializers.py
'''
from rest_framework import serializers

from clubMembers.models import ClubMember
from events.models import Event
from participants.models import Participant


class ParticipantCreateSerializer(serializers.ModelSerializer):
    club_member_id = serializers.PrimaryKeyRelatedField(
        queryset=ClubMember.objects.all(),
        source='club_member'
    )
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        source='event',
        required=False # json 으로 받는게 아닌 Event Serializer에서 주입받기 때문에 required=false
    )

    class Meta:
        managed = True
        model = Participant
        fields = ['participant_id', 'club_member_id', 'event_id',
                  'team_type', 'group_type', 'handicap', 'sum_score', 'rank']

    def create(self, validated_data):
        return Participant.objects.create(**validated_data)
