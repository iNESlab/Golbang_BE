from django.test import TestCase
from django.contrib.auth import get_user_model
from clubs.models import Club, ClubMember
from events.models import Event
from participants.models import Participant

User = get_user_model()

class ParticipantPointCalculationTest(TestCase):

    def setUp(self):
        """
        테스트에 필요한 더미 데이터를 생성합니다.
        """
        # 더미 유저 생성
        self.user1 = User.objects.create_user(email='user1@example.com', user_id='user1', password='test123')
        self.user2 = User.objects.create_user(email='user2@example.com', user_id='user2', password='test123')
        self.user3 = User.objects.create_user(email='user3@example.com', user_id='user3', password='test123')
        self.user4 = User.objects.create_user(email='user4@example.com', user_id='user4', password='test123')
        self.user5 = User.objects.create_user(email='user5@example.com', user_id='user5', password='test123')

        # 더미 클럽 생성
        self.club = Club.objects.create(name='Golf Club')

        # 더미 클럽 멤버 생성
        self.member1 = ClubMember.objects.create(user=self.user1, club=self.club)
        self.member2 = ClubMember.objects.create(user=self.user2, club=self.club)
        self.member3 = ClubMember.objects.create(user=self.user3, club=self.club)
        self.member4 = ClubMember.objects.create(user=self.user4, club=self.club)
        self.member5 = ClubMember.objects.create(user=self.user5, club=self.club)

        # 더미 이벤트 생성
        self.event = Event.objects.create(club=self.club, event_title='Golf Tournament')

        # 더미 참가자 생성
        self.participant1 = Participant.objects.create(club_member=self.member1, event=self.event, rank='1', group_type=Participant.GroupType.GROUP1)
        self.participant2 = Participant.objects.create(club_member=self.member2, event=self.event, rank='T2', group_type=Participant.GroupType.GROUP1)
        self.participant3 = Participant.objects.create(club_member=self.member3, event=self.event, rank='T2', group_type=Participant.GroupType.GROUP1)
        self.participant4 = Participant.objects.create(club_member=self.member4, event=self.event, rank='4', group_type=Participant.GroupType.GROUP1)
        self.participant5 = Participant.objects.create(club_member=self.member5, event=self.event, rank='5', group_type=Participant.GroupType.GROUP1)

    def test_calculate_points(self):
        """
        참가자들의 포인트가 올바르게 계산되는지 테스트합니다.
        """

        # 모든 참가자의 포인트 계산
        for participant in Participant.objects.filter(event=self.event):
            participant.calculate_points()

        # 각 참가자의 예상 포인트
        expected_points = {
            self.participant1: 7,  # Rank "1": 5 (점수) + 2 (출석 점수)
            self.participant2: 6,  # Rank "T2": 4 (점수) + 2 (출석 점수)
            self.participant3: 6,  # Rank "T2": 4 (점수) + 2 (출석 점수)
            self.participant4: 4,  # Rank "4": 2 (점수) + 2 (출석 점수)
            self.participant5: 3,  # Rank "5": 1 (점수) + 2 (출석 점수)
        }

        # 각 참가자에 대해 예상 포인트와 실제 포인트를 비교
        for participant, expected_point in expected_points.items():
            participant.refresh_from_db()  # 데이터베이스에서 최신 데이터 가져오기
            print(
                f"Participant: {participant.club_member.user.email}, Expected: {expected_point}, Got: {participant.points}")

            self.assertEqual(participant.points, expected_point,
                             f"Participant: {participant.club_member.user.email}, Expected: {expected_point}, Got: {participant.points}")
