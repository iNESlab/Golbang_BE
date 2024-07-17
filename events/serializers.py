# events/serializers.py
from django.db import transaction
from rest_framework import serializers

from clubMembers.models import ClubMember
from .models import Event
from participants.serializers import ParticipantCreateSerializer


class EventCreateSerializer(serializers.ModelSerializer):

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
        fields = ['event_id', 'club_member_id','participants', 'event_title', 'location',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time']
        # club_member_id: param으로 받는 값도 추가해야한다. param -> view (request data에 param 데이터 추가) -> serial

    def create(self, validated_data):
        with transaction.atomic():
            print("출력 확인")
            participant_data = validated_data.pop('participant_set', [])
            print("출력 확인1",participant_data)
            #  이유 불명, club_member_id를 이벤트 객체 생성시 participants든 param으로든 입력받으면,
            #  validated_data.pop('participants_set',[])에서 clubMember(id)가 아닌 ClubMember 객체로 바뀜

            event = Event.objects.create(**validated_data)
            print("출력 확인2")

            # 이벤트 ID를 이용해 각 참가자의 이벤트 필드를 설정
            for participant in participant_data:
                print('로그 participant', participant)
                participant['event_id']=event.pk
                participant['club_member_id'] = participant['club_member'].pk # 객체에서 다시 pk로 변경
                participant_serializer = ParticipantCreateSerializer(data=participant)
                print("로그2",participant_serializer)
                if participant_serializer.is_valid(raise_exception=True):
                    print("로그3", participant_serializer)
                    participant_serializer.save()
            return event
