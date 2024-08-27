'''
MVP demo ver 0.0.8
2024.08.02
participants/views.py

역할: Django Rest Framework(DRF)를 사용하여 이벤트 API 엔드포인트의 로직을 처리
- 참가자 : 자신의 참가 상태를 변경
'''
from django.db.models import Avg, Min, Count

from rest_framework import status
from rest_framework.decorators import permission_classes, action
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


class StatisticsViewSet(viewsets.ViewSet):
    '''
    참가자 개인 통계 클래스
    '''
    permission_classes = [IsAuthenticated]

    def list(self, request):
        '''
        사용 가능한 통계 API의 목록을 반환
        '''
        return Response({
            "status": status.HTTP_200_OK,
            "message": "Statistics API root",
            "data": {
                "endpoints": {
                    "overall": "GET /statistics/overall/",
                    "yearly": "GET /statistics/yearly/{year}/",
                    "period": "GET /statistics/period/?start_date={start_date}&end_date={end_date}",
                    "ranks": "GET /statistics/ranks/?club_id={club_id}",
                    "events": "GET /statistics/events/?club_id={club_id}",
                }
            }
        })

        # StatisticsViewSet 클래스 내부

    @action(detail=False, methods=['get'], url_path='overall')
    def overall_statistics(self, request):
        '''
        전체 통계
        '''
        user = request.user  # 요청을 보낸 사용자를 가져옴
        participants = Participant.objects.filter(club_member__user=user)  # 해당 사용자의 모든 참가 데이터

        if not participants.exists():  # 참가 데이터가 없을 경우, 404
            return handle_404_not_found('participant data', 'for the user')

        # 평균 스코어 계산
        average_score = participants.aggregate(average=Avg('sum_score'))['average'] or 0

        # 베스트 스코어 (최소 스코어) 계산
        best_score = participants.aggregate(best=Min('sum_score'))['best'] or 0

        # 핸디캡 적용 베스트 스코어 (최소 핸디캡 스코어) 계산
        handicap_bests_score = participants.aggregate(best=Min('handicap_score'))['best'] or 0

        # 총 라운드 수 계산
        games_played = participants.count()

        # 응답 데이터 생성
        data = {
            "average_score": round(average_score, 1),
            "best_score": best_score,
            "handicap_bests_score": handicap_bests_score,
            "games_played": games_played
        }

        return Response({
            "status": status.HTTP_200_OK,
            "message": "Successfully retrieved overall statistics",
            "data": data
        }, status=status.HTTP_200_OK)