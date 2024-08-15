'''
MVP demo ver 0.0.4
2024.07.27
events/serializers.py

역할:
Django REST Framework에서 데이터의 직렬화(Serialization)와 역직렬화(Deserialization)를 처리하는 역할로
이벤트(Event) 모델에 대한 직렬화(Serialization) 로직을 정의
기능:
- 이벤트를 JSON 형식으로 변환
- 이벤트 생성/수정/상세 Serializer 구현
'''

# events/serializers.py
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from accounts.models import User
from clubs.models import Club
from participants.models import Participant
from .models import Event
from participants.serializers import ParticipantCreateUpdateSerializer, ParticipantDetailSerializer
from .utils import EventUtils

class EventCreateUpdateSerializer(serializers.ModelSerializer):
    event_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    participants = ParticipantCreateUpdateSerializer(source='participant_set', many=True)
    club_id = serializers.PrimaryKeyRelatedField(
        queryset=Club.objects.all(),
        write_only=True,
        required=False,
        source='club'
    )

    class Meta:
        model = Event
        fields = ['event_id', 'club_id', 'participants', 'event_title', 'location',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time']
        # club_id: param으로 받는 값도 추가해야한다. param -> view (request data에 param 데이터 추가) -> serial

    def create(self, validated_data):
        with transaction.atomic():
            participant_data = validated_data.pop('participant_set', [])
            # id로 받은 값들을 객체로 반환함.
            event = Event.objects.create(**validated_data)

            # 이벤트 ID를 이용해 각 참가자의 이벤트 필드를 설정
            for participant in participant_data:
                participant['event_id']  = event.pk
                participant['member_id'] = participant['club_member'].pk  # 객체에서 다시 pk로 변경
                participant_serializer   = ParticipantCreateUpdateSerializer(data=participant)
                if participant_serializer.is_valid(raise_exception=True):
                    participant_serializer.save()
            return event

    def update(self, instance, validated_data):
        with transaction.atomic():
            participant_data = validated_data.pop('participant_set', [])
            # Event 필드를 업데이트
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            # 기존 참가자 데이터 삭제
            instance.participant_set.all().delete()
            # 새로운 참가자 데이터 추가
            for participant in participant_data:
                participant['event_id'] = instance.id
                participant['member_id'] = participant['club_member'].pk
                participant_serializer = ParticipantCreateUpdateSerializer(data=participant)
                if participant_serializer.is_valid(raise_exception=True):
                    participant_serializer.save()
            return instance


class EventDetailSerializer(serializers.ModelSerializer):
    participants = ParticipantDetailSerializer(source='participant_set', many=True, read_only=True)
    event_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    participants_count = serializers.SerializerMethodField(read_only=True)
    party_count = serializers.SerializerMethodField(read_only=True)
    accept_count = serializers.SerializerMethodField(read_only=True)
    deny_count = serializers.SerializerMethodField(read_only=True)
    pending_count = serializers.SerializerMethodField(read_only=True)
    #TODO: 같은 조 인원을 반환하는 필드 추가해야함
    member_group = serializers.SerializerMethodField(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    date = serializers.DateField(write_only=True, required=False)
    status_type = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Event
        fields = ['event_id', 'participants', 'participants_count', 'party_count','accept_count',
                  'deny_count', 'pending_count', 'event_title', 'location', 'start_date_time', 'end_date_time',
                  'repeat_type', 'game_mode', 'alert_date_time', 'member_group',
                  'user_id', 'date', 'status_type']

    def get_participants_count(self, obj):
        return obj.participant_set.count()
    def get_party_count(self, obj):
        return obj.participant_set.filter(status_type="PARTY").count()
    def get_accept_count(self, obj):
        return obj.participant_set.filter(Q(status_type="ACCEPT") | Q(status_type="PARTY")).count()
    def get_deny_count(self, obj):
        return obj.participant_set.filter(status_type="DENY").count()
    def get_pending_count(self, obj):
        return obj.participant_set.filter(status_type="PENDING").count()
    def get_member_group(self, obj):
        return self.context.get('group_type')

class UserResultSerializer(serializers.ModelSerializer):
    # 사용자의 스트로크와 순위를 계산하여 반환하는 시리얼라이저
    stroke = serializers.SerializerMethodField()    # 동적으로 스트로크값 계산
    rank = serializers.SerializerMethodField()      # 사용자 순위를 계산하기 위한 메서드 필드

    class Meta:
        model = User
        fields = ['user_id', 'name', 'stroke', 'rank']

    def get_stroke(self, obj):
        # GET 요청의 파라미터를 통해 sort_type이 'handicap'인 경우, 핸디캡 점수를 반환
        sort_type = self.context.get('sort_type', 'sum_score')
        event_id = self.context.get('event_id')
        participant = Participant.objects.filter(event_id=event_id, club_member__user=obj).first()
        if sort_type == 'handicap_score':
            return participant.handicap_score if participant else 0
        else:
            return participant.sum_score if participant else 0

    def get_rank(self, obj):
        # 특정 이벤트에서 사용자의 순위를 반환
        event_id = self.context.get('event_id')
        participant = Participant.objects.filter(event_id=event_id, club_member__user=obj).first()
        return participant.rank if participant else None

class EventResultSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField() # 참가자 리스트를 정렬하여 반환
    event_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    user = serializers.SerializerMethodField() # 사용자의 정보를 반환

    class Meta:
        model = Event
        fields = ['user', 'event_id', 'event_title', 'location', 'start_date_time', 'end_date_time', 'game_mode', 'participants']

    def get_participants(self, obj):
        sort_type = self.context.get('sort_type', 'sum_score')
        participants = list(obj.participant_set.all())  # QuerySet을 리스트로 변환

        # 점수를 동적으로 계산
        for participant in participants:
            participant.handicap_score = EventUtils.calculate_handicap_score(participant)
            participant.sum_score = EventUtils.calculate_sum_score(participant)

        # sort_type에 따라 정렬
        if sort_type == 'handicap_score':
            participants = sorted(participants, key=lambda p: p.handicap_score)
        else:
            participants = sorted(participants, key=lambda p: p.sum_score)

        # 순위를 계산하여 할당
        self.assign_ranks(participants, sort_type)

        return ParticipantDetailSerializer(participants, many=True, read_only=True).data

    def assign_ranks(self, participants, sort_type):
        """
        sort_type에 따라 참가자들을 정렬하고, 동점자를 고려한 순위를 계산하여 반환
        동점자인 경우, 앞에 "T"를 붙여 순위에 표시
        """
        previous_score = None
        rank = 1
        tied_rank = 1  # 동점자의 랭크를 별도로 관리

        for idx, participant in enumerate(participants):
            current_score = getattr(participant, sort_type)

            if current_score == previous_score:
                participant.rank = f"T{tied_rank}"  # 이전 참가자와 동일한 점수라면 T로 표기
                participants[idx - 1].rank = f"T{tied_rank}"  # 이전 참가자의 랭크도 T로 업데이트
            else:
                participant.rank = str(rank)  # 새로운 점수일 경우 일반 순위
                tied_rank = rank  # 새로운 점수에서 동점 시작 지점을 설정

            previous_score = current_score
            rank += 1  # 다음 순위로 이동

    def get_user(self, obj):
        # 요청된 사용자 정보를 반환
        user = self.context.get('user')
        sort_type = self.context.get('sort_type', 'sum_score')
        return UserResultSerializer(user, context={'event_id': obj.id, 'sort_type': sort_type}).data
