'''
MVP demo ver 0.0.1
2024.07.15
participants/serializers.py
'''
from rest_framework import serializers

from members.models import Member
from members.serializers import MemberSerializer
from events.models import Event
from participants.models import Participant


class ParticipantCreateSerializer(serializers.ModelSerializer):
    participant_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(),
        source='member'
    )
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        source='event',
        required=False # json 으로 받는게 아닌 Event Serializer에서 주입받기 때문에 required=false
    )

    class Meta:
        managed = True  # True면 장고는 해당 모델에 대해 DB 테이블과 동기화되도록 유지한다. Default True
        model = Participant
        fields = ['participant_id', 'member_id', 'event_id',
                  'team_type', 'group_type', 'sum_score', 'rank']

    def create(self, validated_data):
        return Participant.objects.create(**validated_data)


class ParticipantDetailSerializer(serializers.ModelSerializer):
    participant_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    member = MemberSerializer(read_only=True)
    handicap_score = serializers.SerializerMethodField()
    #TODO: score 테이블 만들어서 연결

    class Meta:
        model = Participant
        fields = ['participant_id', 'member', 'status_type', 'team_type',
                  'group_type', 'sum_score', 'rank', 'handicap_score']

    def get_handicap_score(self, obj):
        return int(obj.sum_score) - int(obj.member.user.handicap)
