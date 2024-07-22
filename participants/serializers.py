'''
MVP demo ver 0.0.1
2024.07.15
participants/serializers.py
'''
from rest_framework import serializers

from clubMembers.models import ClubMember
from clubMembers.serializers import ClubMemberSerializer
from events.models import Event
from participants.models import Participant


class ParticipantCreateSerializer(serializers.ModelSerializer):
    participant_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
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
        managed = True  # True면 장고는 해당 모델에 대해 DB 테이블과 동기화되도록 유지한다. Default True
        model = Participant
        fields = ['participant_id', 'club_member_id', 'event_id',
                  'team_type', 'group_type', 'handicap', 'sum_score', 'rank']
        # TODO: handicap 모델에서 제거시 같이 제거

    def create(self, validated_data):
        return Participant.objects.create(**validated_data)


class ParticipantDetailSerializer(serializers.ModelSerializer):
    participant_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    club_member = ClubMemberSerializer(read_only=True)

    # handicap_plus_score = serializers.SerializerMethodField()
    class Meta:
        model = Participant
        fields = ['participant_id', 'club_member', 'team_type',
                  'group_type', 'handicap', 'sum_score', 'rank']

    # TODO: handicap 모델에서 제거시 같이 제거

    '''
    TODO: ClubMember와 member 외래키 연결 후 주석 해제
    def get_handicap_plus_score(self, obj):
        return obj.club_member.member.handicap + obj.sum_score
    '''