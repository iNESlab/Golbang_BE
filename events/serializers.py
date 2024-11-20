'''
MVP demo ver 0.0.6
2024.08.27
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
from django.db.models import Q, Sum
from rest_framework import serializers

from accounts.models import User
from clubs.models import Club
from clubs.serializers import ClubProfileSerializer
from golf_data.models import GolfClub
from golf_data.serializers import GolfClubSerializer
from participants.models import Participant, HoleScore
from .models import Event
from participants.serializers import ParticipantCreateUpdateSerializer, ParticipantDetailSerializer

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
        fields = ['event_id', 'club_id', 'participants', 'event_title', 'location', 'site',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time']
        #TODO club_id: param으로 받는 값도 추가해야한다. param -> view (request data에 param 데이터 추가) -> serial

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
    club = ClubProfileSerializer(read_only=True)
    golf_club = serializers.SerializerMethodField()  # GolfClub 상세 정보를 위한 필드
    my_participant_id = serializers.SerializerMethodField(read_only=True)
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
        fields = ['club', 'event_id', 'my_participant_id', 'participants', 'participants_count', 'party_count','accept_count',
                  'deny_count', 'pending_count', 'event_title', 'location', 'site', 'golf_club', 'start_date_time', 'end_date_time',
                  'repeat_type', 'game_mode', 'alert_date_time', 'member_group',
                  'user_id', 'date', 'status_type']

    def get_golf_club(self, obj):
        # site 필드와 club_name이 일치하는 GolfClub 객체를 직렬화하여 반환
        golf_club = GolfClub.objects.filter(club_name=obj.site).first()
        if golf_club:
            return GolfClubSerializer(golf_club).data
        return None

    def get_my_participant_id(self, obj):
        self.my_participant_id = obj.participant_set.filter(club_member__user=self.context['request'].user).first().id
        return self.my_participant_id
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
        return obj.participant_set.filter(id=self.my_participant_id).first().group_type

class UserResultSerializer(serializers.ModelSerializer):
    # 사용자의 스트로크와 순위를 계산하여 반환하는 시리얼라이저
    sum_score = serializers.SerializerMethodField()    # 동적으로 스코어값 계산
    handicap_score = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()      # 사용자 순위를 계산하기 위한 메서드 필드
    handicap_rank = serializers.SerializerMethodField() # 핸디캡 순위를 계산하기 위한 메서드 필드
    scorecard = serializers.SerializerMethodField() # 스코어카드 데이터 반환

    class Meta:
        model = User
        fields = ['user_id', 'profile_image', 'name', 'sum_score', 'handicap_score', 'rank', 'handicap_rank',  'scorecard']

    def get_sum_score(self, obj):
        # 현재 이벤트 및 사용자 정보를 바탕으로 참가자를 조회
        event_id = self.context.get('event_id')
        participant = Participant.objects.filter(event_id=event_id, club_member__user=obj).first()

        if participant:
            return participant.sum_score
        return 0  # 참가자가 없을 경우 기본값 반환

    def get_handicap_score(self, obj):
        event_id = self.context.get('event_id')
        participants = Participant.objects.filter(event_id=event_id, club_member__user=obj).first()
        if participants:
            return participants.handicap_score
        return 0  # 참가자가 없을 경우 기본값 반환

    def get_rank(self, obj):
        # 특정 이벤트에서 사용자의 일반 순위를 반환
        event_id = self.context.get('event_id')
        participant = Participant.objects.filter(event_id=event_id, club_member__user=obj).first()

        return participant.rank if participant else None

    def get_handicap_rank(self, obj):
        # 특정 이벤트에서 사용자의 핸디캡 순위를 반환
        event_id = self.context.get('event_id')
        participant = Participant.objects.filter(event_id=event_id, club_member__user=obj).first()

        return participant.handicap_rank if participant else None

    def get_scorecard(self, obj):
        event_id = self.context.get('event_id')
        participant = Participant.objects.filter(event_id=event_id, club_member__user=obj).first()

        if participant:
            scorecard = participant.get_scorecard()
            return scorecard if scorecard else []

class EventResultSerializer(serializers.ModelSerializer):
    """
    이벤트 결과를 반환하는 시리얼라이저
    """
    participants = serializers.SerializerMethodField()  # 참가자 리스트를 반환
    event_id = serializers.IntegerField(source='id', read_only=True)  # 여기서 'id' 필드를 'event_id'로 매핑
    user = serializers.SerializerMethodField()  # 사용자의 정보를 반환

    class Meta:
        model = Event
        fields = ['user', 'event_id', 'event_title', 'location', 'site', 'start_date_time', 'end_date_time', 'game_mode', 'participants']

    def get_participants(self, obj):
        # 컨텍스트에서 참가자 리스트를 가져와 정렬
        participants = self.context.get('participants')
        sort_type = self.context.get('sort_type', 'sum_score')

        if sort_type == 'handicap_score':
            participants = sorted(participants, key=lambda p: p.handicap_score)
        else:
            participants = sorted(participants, key=lambda p: p.sum_score)

        return ParticipantDetailSerializer(participants, many=True).data

    def get_user(self, obj):
        user = self.context['request'].user
        return UserResultSerializer(user, context={'event_id': obj.id}).data
    
    
class ScoreCardSerializer(serializers.ModelSerializer):
    """
    스코어카드 결과(그룹별 스코어 결과)를 반환하는 시리얼라이저
    """
    participant_name = serializers.CharField(source='club_member.user.name', read_only=True)
    front_nine_score = serializers.SerializerMethodField()  # 전반전 점수 (1~9홀)
    back_nine_score = serializers.SerializerMethodField() # 후반전 점수 (10~18홀)
    total_score = serializers.SerializerMethodField()
    handicap_score = serializers.SerializerMethodField()
    scorecard = serializers.SerializerMethodField()         # 모델의 get_scorecard 메서드를 활용

    class Meta:
        model = Participant
        fields = ['participant_name', 'front_nine_score', 'back_nine_score', 'total_score', 'handicap_score', 'scorecard']

    def get_front_nine_score(self, participant):
        front_nine_score = HoleScore.objects.filter(participant=participant, hole_number__lte=9).aggregate(total=Sum('score'))['total']
        return front_nine_score or 0

    def get_back_nine_score(self, participant):
        back_nine_score = HoleScore.objects.filter(participant=participant, hole_number__gte=10).aggregate(total=Sum('score'))['total']
        return back_nine_score or 0

    def get_total_score(self, participant):
        total_score = HoleScore.objects.filter(participant=participant).aggregate(total=Sum('score'))['total']
        return total_score or 0

    def get_handicap_score(self, participant):
        total_score = self.get_total_score(participant)
        handicap_score = total_score - participant.club_member.user.handicap
        return handicap_score

    def get_scorecard(self, participant):
        return participant.get_scorecard() or []
