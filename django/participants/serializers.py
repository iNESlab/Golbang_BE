'''
MVP demo ver 0.0.8
2024.08.02
participants/serializers.py

역할:
Django REST Framework에서 데이터의 직렬화(Serialization)와 역직렬화(Deserialization)를 처리하는 역할로
참가자(Participant) 모델에 대한 직렬화(Serialization) 로직을 정의
기능:
- Participant를 JSON 형식으로 변환
- Participant 생성 / 수정 / 상세 / 자동 매칭 Serializer 구현
'''
from django.db.models import Sum
from rest_framework import serializers

from clubs.models import ClubMember
from clubs.serializers import ClubMemberSerializer
from events.models import Event
from participants.models import Participant, HoleScore


class ParticipantCreateUpdateSerializer(serializers.ModelSerializer):
    '''
    참가자 생성 및 업데이트 시리얼라이저
    '''
    participant_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=ClubMember.objects.all(),
        source='club_member'
    )
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        source='event',
        required=False # json 으로 받는게 아닌 Event Serializer에서 주입받기 때문에 required=false
    )
    sum_score = serializers.SerializerMethodField(read_only=True)
    rank = serializers.IntegerField(read_only=True)
    status_type = serializers.CharField(read_only=True)
    class Meta:
        managed = True  # True면 장고는 해당 모델에 대해 DB 테이블과 동기화되도록 유지한다. Default True
        model = Participant
        fields = ['participant_id', 'member_id', 'event_id',
                  'team_type', 'group_type', 'sum_score', 'rank', 'handicap_rank', 'status_type']


    def get_sum_score(self, obj):
        total_score = HoleScore.objects.filter(participant=obj).aggregate(total=Sum('score'))['total']

        return total_score

class ParticipantDetailSerializer(serializers.ModelSerializer):
    '''
    참가자 상세정보를 반환하는 시리얼라이저
    '''
    participant_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    member = ClubMemberSerializer(source='club_member', read_only=True)
    sum_score = serializers.SerializerMethodField(read_only=True)
    handicap_score = serializers.SerializerMethodField(read_only=True)
    hole_number = serializers.SerializerMethodField(read_only=True) # 마지막 홀 번호 반환하는 메서드 필드

    class Meta:
        model = Participant
        fields = ['participant_id', 'member', 'status_type', 'team_type', 'hole_number',
                  'group_type', 'sum_score', 'rank', 'handicap_rank', 'handicap_score']
    def get_hole_number(self, obj):
        # 마지막 홀 넘버 반환
        hole_score = HoleScore.objects.filter(participant=obj).order_by('-hole_number').first()
        return hole_score.hole_number if hole_score else None

    def get_sum_score(self, obj):
        return HoleScore.objects.filter(participant=obj).aggregate(total=Sum('score'))['total']

    def get_handicap_score(self, obj):
        return int(obj.sum_score) - int(obj.club_member.user.handicap)

class ParticipantAutoMatchSerializer(serializers.ModelSerializer):
    '''
    참가자 자동 매칭 정보 반환 시리얼라이저
    '''
    member_id = serializers.PrimaryKeyRelatedField(
        queryset=ClubMember.objects.all(),
        source='club_member'
    )
    member = ClubMemberSerializer(read_only=True)
    handicap = serializers.SerializerMethodField(read_only=True)
    team_type = serializers.CharField(read_only=True)
    group_type = serializers.CharField(read_only=True)

    class Meta:
        model = Participant
        fields = ['member_id', 'member', 'handicap', 'team_type', 'group_type']

    def get_handicap(self, obj):
        # obj가 dict인 경우 처리
        if isinstance(obj, dict):
            club_member = obj.get('club_member')
            if isinstance(club_member, ClubMember):
                return club_member.user.handicap
        # obj가 Participant 모델 인스턴스인 경우 처리
        elif isinstance(obj, Participant):
            return obj.club_member.user.handicap
        return None

class HoleScoreSerializer(serializers.ModelSerializer):
    '''
    홀 정보 시리얼라이저
    '''
    participant_id = serializers.PrimaryKeyRelatedField(
        queryset   = Participant.objects.all(),
        source     = 'participant'
    )
    action = serializers.CharField(write_only=True)
    class Meta:
        model  = HoleScore
        fields = ['action', 'participant_id', 'hole_number', 'score']


class ParticipantEventStatisticsSerializer(serializers.ModelSerializer):
    """
    이벤트 종료 후, 한 이벤트에 대해 모든 참가자들의 통계 정보를 반환하는 시리얼라이저
    """
    participant_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    total_points = serializers.SerializerMethodField(read_only=True)
    total_participants  = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Participant
        fields = ['participant_id', 'sum_score', 'handicap_score',  'rank', 'handicap_rank', 'points', 'total_points', 'total_participants']

    def get_total_participants(self, obj):
        """
        이벤트에 참여한 전체 참가자 수 반환
        """
        return Participant.objects.filter(event=obj.event).count()

    def get_total_points(self, obj):
        """
        클럽 멤버의 전체 포인트를 반환
        """
        # Participant의 club_member 필드를 통해 ClubMember 인스턴스를 가져옴
        club_member = obj.club_member

        # ClubMember 인스턴스의 total_points를 업데이트하고 반환
        club_member.update_total_points()
        return club_member.total_points

class EventStatisticsSerializer(serializers.ModelSerializer):
    """
    각 이벤트에 대한 참가자(본인) 통계를 직렬화하는 시리얼라이저
    """
    event_id = serializers.PrimaryKeyRelatedField(source='event.id', read_only=True)
    event_name = serializers.CharField(source='event.event_title', read_only=True)
    total_participants = serializers.SerializerMethodField()

    class Meta:
        model = Participant
        fields = ['event_id', 'event_name', 'sum_score', 'handicap_score', 'points',
                  'total_participants', 'rank', 'handicap_rank']

    def get_total_participants(self, obj):
        """
        이벤트에 참여한 전체 참가자 수 반환 (ACCEPT와 PARTY 상태인 참가자만 포함)
        """
        return Participant.objects.filter(event=obj.event, status_type__in=['ACCEPT', 'PARTY']).count()
