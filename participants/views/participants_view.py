'''
MVP demo ver 0.0.8
2024.08.02
participants/views/participants_view.py

역할: Django Rest Framework(DRF)를 사용하여 참가자 API 엔드포인트의 로직을 처리
- 참가자 : 자신의 참가 상태를 변경
'''

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

            find_user=participant.club_member.user # 참가자에 대한 사용자 정보
            if not find_user == user:
                return handle_401_unauthorized(f'해당 참가자({find_user.name})가 아닙니다.')

            participant.status_type = status_type   # 상태 타입 업데이트
            participant.save()

            serializer = ParticipantCreateUpdateSerializer(participant)

            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully participant status_type update',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Participant.DoesNotExist: # 참가자가 존재하지 않을 경우
            return handle_404_not_found('participant', kwargs['pk'])
        except Exception as e: # 기타 예외 처리
            return handle_400_bad_request({'error': str(e)})
