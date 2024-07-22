# events/serializers.py
from django.db import transaction
from rest_framework import serializers

from clubMembers.models import ClubMember
from .models import Event
from participants.serializers import ParticipantCreateSerializer, ParticipantDetailSerializer


class EventCreateSerializer(serializers.ModelSerializer):
    event_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    participants = ParticipantCreateSerializer(source='participant_set', many=True)
    club_member_id = serializers.PrimaryKeyRelatedField(
        queryset=ClubMember.objects.all(),
        write_only=True,
        required=True,
        source='club_member'
    )
    # request json으로 club_member_id를 받고 이를 ClubMember의 필드인 club_member와 매핑한다.

    class Meta:
        model = Event
        fields = ['event_id', 'club_member_id', 'participants', 'event_title', 'location',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time']
        # club_member_id: param으로 받는 값도 추가해야한다. param -> view (request data에 param 데이터 추가) -> serial

    def create(self, validated_data):
        with transaction.atomic():
            participant_data = validated_data.pop('participant_set', [])
            #  이유 불명, club_member_id를 이벤트 객체 생성시 participants든 param으로든 입력받으면,
            #  validated_data.pop('participants_set',[])에서 clubMember(id)가 아닌 ClubMember 객체로 바뀜

            event = Event.objects.create(**validated_data)

            # 이벤트 ID를 이용해 각 참가자의 이벤트 필드를 설정
            for participant in participant_data:
                participant['event_id'] = event.pk
                participant['club_member_id'] = participant['club_member'].pk  # 객체에서 다시 pk로 변경
                participant_serializer = ParticipantCreateSerializer(data=participant)
                if participant_serializer.is_valid(raise_exception=True):
                    participant_serializer.save()
            return event


class EventDetailSerializer(serializers.ModelSerializer):
    participants = ParticipantDetailSerializer(source='participant_set', many=True, read_only=True)
    event_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    club_member_id = serializers.PrimaryKeyRelatedField(
        queryset=ClubMember.objects.all(),
        required=True,
        source='club_member'
    )

    class Meta:
        model = Event
        fields = ['event_id', 'club_member_id', 'participants', 'event_title', 'location',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time']
