'''
MVP demo ver 0.0.8
2024.08.02
participants/views/participants_view.py

역할: Django Rest Framework(DRF)를 사용하여 참가자 API 엔드포인트의 로직을 처리
- 참가자 : 자신의 참가 상태를 변경
'''

import asyncio
from dataclasses import asdict
import logging
from asgiref.sync import async_to_sync
from rest_framework import status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.decorators import action

from participants.models import Participant
from participants.serializers import ParticipantCreateUpdateSerializer
from utils.error_handlers import handle_400_bad_request, handle_404_not_found, handle_401_unauthorized
from participants.stroke.data_class import ParticipantRedisData
from participants.stroke.mysql_interface import MySQLInterface
from participants.stroke.redis_interface import RedisInterface

@permission_classes([IsAuthenticated])
class ParticipantViewSet(viewsets.ModelViewSet, RedisInterface, MySQLInterface):
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
        
    @action(detail=False, methods=["post"], url_path="group/stroke")
    def input_score(self, request, pk=None):
        try:
            score = request.data.get("score")
            hole_number = request.data.get("hole_number")
            event_id = request.data.get("event_id")
            participant_id = request.data.get("participant_id")
            if score is None or event_id is None:
                logging.info("score or event_id 필드가 필요합니다.")
                return handle_400_bad_request("score or event_id 필드가 필요합니다.")
            
             # 🟡 Redis에서 참가자 정보 가져오기
            participant_redis: ParticipantRedisData = async_to_sync(self.get_participant_from_redis)(event_id, participant_id)
            logging.info(f"participant_redis: {participant_redis}")

            # 🔵 없으면 MySQL에서 가져와 Redis에 저장
            if participant_redis is None:
                participant_mysql = Participant.objects.select_related("club_member__user").get(pk=participant_id)
                if participant_mysql is None:
                    logging.info(f"participant_mysql: {participant_mysql}")
                    return handle_404_not_found('participant', participant_id)

                participant_redis = async_to_sync(self.save_participant_in_redis)(participant_mysql)
                print(f"participant_redis saved: {participant_redis}, type: {type(participant_redis)}")
            
            # ✅ Redis에 스코어 저장 및 랭킹 업데이트
            async_to_sync(self.update_hole_score_in_redis)(participant=participant_redis, hole_number=hole_number, score=score)
            async_to_sync(self.update_rankings_in_redis)(event_id=event_id)

            update_participant_redis: ParticipantRedisData = async_to_sync(self.get_participant_from_redi)(event_id, participant_id)
            if update_participant_redis is None:
                logging.info(f"존재하지 않는 참가자입니다. participant_id: {participant_id}")
                return handle_404_not_found(f'존재하지 않은 참가자입니다. participant_id: {participant_id}')
            
            # ✅ Celery 마이그레이션 관리도 호출 (기존 WebSocket 로직 그대로)
            async_to_sync(self.save_celery_event_from_redis_to_mysql)(event_id, is_count_incr=False)

            response_data = asdict(update_participant_redis)

            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully updated participant score',
                'data': response_data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logging.info(f"Error in input_score: {str(e)}")
            return handle_400_bad_request({'error': str(e)})
        
    @action(detail=True, methods=["get"], url_path="group/stroke")
    def get_group_stroke(self, request, pk=None):
        try:
            event_id = request.data.get("event_id")
            group_type = request.data.get("group_type")
            # 그룹에 속한 모든 참가자를 한 번의 쿼리로 가져옴
            participants = async_to_sync(self.get_group_participants_from_redis)(event_id, group_type)
            print(f'participants: {participants}')
            # 각 참가자의 홀 스코어를 비동기로 병렬 처리
            group_scores = async_to_sync(asyncio.gather)(*[
            self.process_participant(participant) for participant in participants
        ])
            print(f'group_scores: {group_scores}')

            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully retrieved group stroke',
                'data': group_scores
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error in get_group_stroke: {str(e)}")
            return handle_400_bad_request({'error': str(e)})

    async def process_participant(self, participant: ParticipantRedisData):
        participant_id = participant.participant_id
        hole_scores = await self.get_all_hole_scores_from_redis(participant_id)
        print(f'hole_scores:{hole_scores}')
        return {
            'participant_id': participant_id,
            'user_name': participant.user_name,
            'group_type': participant.group_type,
            'team_type': participant.team_type,
            'is_group_win': participant.is_group_win,
            'is_group_win_handicap': participant.is_group_win_handicap,
            'sum_score': participant.sum_score,
            'handicap_score': participant.handicap_score,
            'scores': hole_scores,
        }
