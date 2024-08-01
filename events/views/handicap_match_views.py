# views.py

from rest_framework import viewsets
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import math
import random

from clubs.models import ClubMember
from participants.serializers import ParticipantAutoMatchSerializer
from utils.error_handlers import handle_400_bad_request

@permission_classes([IsAuthenticated])
class HandicapMatchViewSet(viewsets.ViewSet):

    def create(self, request):
        competition_type = request.data.get('competition_type')
        group_head_count = request.data.get('group_head_count')
        team_head_count = request.data.get('team_head_count')
        members_data = request.data.get('participants')

        if competition_type is None:
            return handle_400_bad_request('Missing competition_type parameter')

        if competition_type == 'personal':
            if group_head_count is None:
                return handle_400_bad_request('Missing group_head_count parameter')
            try:
                group_head_count = int(group_head_count)
            except ValueError:
                return handle_400_bad_request('group_head_count must be an integer')
            return self.personal_competition(members_data, group_head_count)

        elif competition_type == 'team':
            if team_head_count is None:
                return handle_400_bad_request('Missing team_head_count parameter')
            try:
                team_head_count = int(team_head_count)
            except ValueError:
                return handle_400_bad_request('team_head_count must be an integer')
            return self.team_competition(members_data, team_head_count)

        else:
            return handle_400_bad_request('Invalid competition type')

    def personal_competition(self, members_data, group_head_count):
        member_ids = [member['member_id'] for member in members_data]
        members = ClubMember.objects.filter(id__in=member_ids).select_related('user').order_by('user__handicap')
        print('members',members)

        groups = []
        group_size = math.ceil(len(members) / group_head_count)
        print('Group size: ', group_size)
        for i in range(group_head_count):
            group_participants = members[i * group_size:(i + 1) * group_size]
            print('group_participants', group_participants)
            participant_data = [
                {
                    'member_id': member.id,
                    'group_type': i + 1,
                    'team_type': 'NONE',
                }
                for member in group_participants
            ]
            print('participant_data', participant_data)
            serializer = ParticipantAutoMatchSerializer(data=participant_data, many=True)
            if not serializer.is_valid():
                return handle_400_bad_request('참가자 정보를 다시 확인해주세요.')
            groups.append(serializer.data)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved personal competition groups',
            'data': groups
        }

        return Response(response_data, status=status.HTTP_200_OK)

    def team_competition(self, members_data, team_head_count):
        member_ids = [member['member_id'] for member in members_data]
        members = list(ClubMember.objects.filter(id__in=member_ids).select_related('user').order_by('user__handicap'))

        # Step 2: Calculate maximum number of teams (j)
        max_teams = math.ceil(len(members) / team_head_count)

        # Step 3: Divide participants into max_teams groups
        divided_groups = [members[i::max_teams] for i in range(max_teams)]

        # Step 4: Shuffle each group and distribute participants into teams
        teams = [[] for _ in range(max_teams)]
        for divided_group in divided_groups:
            random.shuffle(divided_group)
            for i, member in enumerate(divided_group):
                teams[i % max_teams].append(member)

        response_groups = []
        team_types = ['A', 'B']
        for group_num, group in enumerate(teams):
            participant_data = [
                {
                    'member_id': member.id,
                    'group_type': group_num + 1,
                    'team_type': team_types[group_num % len(team_types)],
                }
                for member in group
            ]
            serializer = ParticipantAutoMatchSerializer(data=participant_data, many=True)
            if serializer.is_valid():
                response_groups.append(serializer.data)
            else:
                return handle_400_bad_request(f'{serializer.errors}')

        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved team competition groups',
            'data': response_groups
        }
        return Response(response_data, status=status.HTTP_200_OK)