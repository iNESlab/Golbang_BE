from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets

from participants.models import Participant
from participants.serializers import ParticipantCreateUpdateSerializer
from utils.error_handlers import handle_400_bad_request, handle_404_not_found, handle_401_unauthorized

@permission_classes([IsAuthenticated])
class ParticipantViewSet(viewsets.ModelViewSet):
    queryset = Participant.objects.all()
    serializer_class = ParticipantCreateUpdateSerializer

    def partial_update(self, request, *args, **kwargs):
        try:
            user = self.request.user
            status_type = self.request.query_params.get('status_type')
            if status_type not in Participant.StatusType.__members__:
                return handle_400_bad_request(f'status_type: {status_type} 이 잘못되었습니다.  '
                                              f'올바른 status_type : ACCEPT, PARTY, DENY, PENDING')

            participant = Participant.objects.get(pk=kwargs['pk'])

            find_user=participant.club_member.user
            if not find_user == user:
                return handle_401_unauthorized(f'해당 참가자({find_user.name})가 아닙니다.')

            participant.status_type = status_type
            participant.save()

            serializer = ParticipantCreateUpdateSerializer(participant)

            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully participant status_type update',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Participant.DoesNotExist:
            return handle_404_not_found('participant', kwargs['pk'])
        except Exception as e:
            return handle_400_bad_request({'error': str(e)})