"""
MVP demo ver 0.0.6
2024.08.27
events/serializers.py

역할:
Django REST Framework에서 데이터의 직렬화(Serialization)와 역직렬화(Deserialization)를 처리하는 역할로
이벤트(Event) 모델에 대한 직렬화(Serialization) 로직을 정의
기능:
- 이벤트를 JSON 형식으로 변환
- 이벤트 생성/수정/상세 Serializer 구현
"""

# events/serializers.py
from django.db import transaction
from django.db.models import Q, Sum
from rest_framework import serializers

from accounts.models import User
from clubs.models import Club
from clubs.serializers import ClubProfileSerializer
from golf_data.models import GolfClub, GolfCourse
from golf_data.serializers import GolfClubBaseSerializer, GolfCourseDetailSerializer
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
    golf_club_id = serializers.PrimaryKeyRelatedField(
        queryset=GolfClub.objects.all(),
        source='golf_club'
    )
    golf_course_id = serializers.PrimaryKeyRelatedField(
        queryset=GolfCourse.objects.all(),
        source='golf_course'
    )

    class Meta:
        model = Event
        # TODO: 프론트에서 'golf_club_id', 'golf_course_id' 추가한 이후에 site 제거하기
        fields = ['event_id', 'club_id', 'participants', 'event_title', 'location', 'site', 'golf_club_id', 'golf_course_id',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time']
        # TODO club_id: param으로 받는 값도 추가해야한다. param -> view (request data에 param 데이터 추가) -> serial

    def create(self, validated_data):
        with transaction.atomic():
            participant_data = validated_data.pop('participant_set', [])
            # id로 받은 값들을 객체로 반환함.
            event = Event.objects.create(**validated_data)

            # 이벤트 ID를 이용해 각 참가자의 이벤트 필드를 설정
            for participant in participant_data:
                participant['event_id'] = event.pk
                participant['member_id'] = participant['club_member'].pk  # 객체에서 다시 pk로 변경
                participant_serializer = ParticipantCreateUpdateSerializer(data=participant)
                if participant_serializer.is_valid(raise_exception=True):
                    participant_serializer.save()
            return event

    def update(self, instance, validated_data):
        with transaction.atomic():
            participant_data = validated_data.pop('participant_set', [])
            # Event 모델의 필드 업데이트
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            # print(f"[DEBUG] Event 업데이트 완료: id={instance.id}")

            # Step 1: 기존 참가자 조회 (club_member.id 기준)
            existing_participants = {p.club_member.id: p for p in instance.participant_set.all()}
            # print(f"[DEBUG] 기존 참가자 수: {len(existing_participants)}")

            # Step 2: 새로 전달된 참가자 데이터 처리
            for participant in participant_data:
                # 반드시 serializer가 요구하는 필드들을 설정합니다.
                participant['event_id'] = instance.id
                participant['member_id'] = participant['club_member'].pk
                member_id = participant['club_member'].pk
                # print(f"[DEBUG] 처리 중인 참가자 - club_member id: {member_id}")

                if member_id in existing_participants:
                    # 이미 존재하는 참가자 업데이트 (status_type 유지)
                    existing_instance = existing_participants.pop(member_id)
                    # print(f"[DEBUG] 기존 참가자 발견: club_member id={member_id}, 현재 status_type={existing_instance.status_type}")

                    # 클라이언트에서 status_type을 명시하지 않은 경우 기존 값을 유지
                    if 'status_type' not in participant:
                        participant['status_type'] = existing_instance.status_type
                        print(f"[DEBUG] status_type 미전달 -> 기존 값 유지: {existing_instance.status_type}")
                    else:
                        print(f"[DEBUG] 클라이언트에서 전달한 status_type: {participant['status_type']}")
                    participant_serializer = ParticipantCreateUpdateSerializer(
                        instance=existing_instance, data=participant, partial=True
                    )
                    participant_serializer.is_valid(raise_exception=True)
                    participant_serializer.save()
                    # print(f"[DEBUG] 참가자 업데이트 완료: club_member id {member_id}")
                else:
                    # 신규 참가자 생성; 이 경우 status_type이 없으면 기본값(PENDING)이 적용됨
                    # print(f"[DEBUG] 신규 참가자 생성: club_member id {member_id}")
                    participant_serializer = ParticipantCreateUpdateSerializer(data=participant)
                    participant_serializer.is_valid(raise_exception=True)
                    participant_serializer.save()
                    # print(f"[DEBUG] 신규 참가자 생성 완료: club_member id {member_id}")

            # Step 3 (선택사항): 새 데이터에 포함되지 않은 기존 참가자 삭제
            for remaining in existing_participants.values():
                # print(f"[DEBUG] 남은 기존 참가자 삭제: club_member id {remaining.club_member.id}")
                remaining.delete()

            # print("[DEBUG] 이벤트 업데이트 전체 완료")
            return instance


# TODO: 이벤트 상세 조회와 이벤트 전체 조회 시리얼라이저 분리.
#  이벤트 상세 조회에서 너무 많은 정보가 담겨 over fetching 되고 있음.
#  이를 해결하고자 이벤트 전체 조회용 시리얼라이저 미리 생성. 단, 프론트엔드에서 준비가 되어야 하므로, 준비된 후에 연결할 예정
class EventListSerializer(serializers.ModelSerializer):
    club = ClubProfileSerializer(read_only=True)
    my_participant_id = serializers.SerializerMethodField(read_only=True)
    event_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    date = serializers.DateField(write_only=True, required=False)
    status_type = serializers.CharField(write_only=True, required=False)
    golf_club_name = serializers.CharField(source='golf_club.club_name', read_only=True)
    golf_course_name = serializers.CharField(source='golf_course.course_name', read_only=True)

    class Meta:
        model = Event
        fields = ['club', 'event_id', 'my_participant_id',
                  'event_title', 'location', 'site', 'golf_club_name', 'golf_course_name',
                  'start_date_time', 'end_date_time',
                  'user_id', 'date', 'status_type']

    def get_my_participant_id(self, obj):
        self.my_participant_id = obj.participant_set.filter(club_member__user=self.context['request'].user).first().id
        return self.my_participant_id

class EventDetailSerializer(serializers.ModelSerializer):
    club = ClubProfileSerializer(read_only=True)
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
    golf_club = GolfClubBaseSerializer(read_only=True)
    golf_course = GolfCourseDetailSerializer(read_only=True)

    class Meta:
        model = Event
        fields = ['club', 'event_id', 'my_participant_id', 'participants', 'participants_count', 'party_count',
                  'accept_count',
                  'deny_count', 'pending_count', 'event_title', 'location', 'site', 'golf_club', 'golf_course',
                  'start_date_time', 'end_date_time', 'repeat_type', 'game_mode', 'alert_date_time', 'member_group',
                  'user_id', 'date', 'status_type']

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
    sum_score = serializers.SerializerMethodField()  # 동적으로 스코어값 계산
    handicap_score = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()  # 사용자 순위를 계산하기 위한 메서드 필드
    handicap_rank = serializers.SerializerMethodField()  # 핸디캡 순위를 계산하기 위한 메서드 필드
    scorecard = serializers.SerializerMethodField()  # 스코어카드 데이터 반환

    class Meta:
        model = User
        fields = ['user_id', 'profile_image', 'name', 'sum_score', 'handicap_score', 'rank', 'handicap_rank',
                  'scorecard']

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
        fields = ['user', 'event_id', 'event_title', 'location', 'site', 'start_date_time', 'end_date_time',
                  'game_mode', 'participants']

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
    team = serializers.SerializerMethodField()  # 팀 정보
    front_nine_score = serializers.SerializerMethodField()  # 전반전 점수 (1~9홀)
    back_nine_score = serializers.SerializerMethodField()  # 후반전 점수 (10~18홀)
    total_score = serializers.SerializerMethodField()
    handicap_score = serializers.SerializerMethodField()
    scorecard = serializers.SerializerMethodField()  # 모델의 get_scorecard 메서드를 활용

    class Meta:
        model = Participant
        fields = ['participant_name', 'team', 'front_nine_score', 'back_nine_score', 'total_score', 'handicap_score',
                  'scorecard']

    def get_team(self, participant):
        # 팀 정보를 반환
        if participant.team_type == Participant.TeamType.TEAM1:
            return "Team A"
        elif participant.team_type == Participant.TeamType.TEAM2:
            return "Team B"
        return "No Team"

    def get_front_nine_score(self, participant):
        front_nine_score = \
        HoleScore.objects.filter(participant=participant, hole_number__lte=9).aggregate(total=Sum('score'))['total']
        return front_nine_score or 0

    def get_back_nine_score(self, participant):
        back_nine_score = \
        HoleScore.objects.filter(participant=participant, hole_number__gte=10).aggregate(total=Sum('score'))['total']
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
