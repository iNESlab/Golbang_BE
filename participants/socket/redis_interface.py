from asgiref.sync import sync_to_async
import redis

from participants.models import Participant

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)

class RedisInterface:
    async def get_participant_ids_from_redis(self):
        keys = await sync_to_async(redis_client.keys)('participant:*')
        participant_ids = list(set(key.decode('utf-8').split(':')[1] for key in keys))
        return participant_ids

    async def update_hole_score_in_redis(self, participant_id, hole_number, score):
        key = f'participant:{participant_id}:hole:{hole_number}'
        await sync_to_async(redis_client.set)(key, score)
        await sync_to_async(redis_client.expire)(key, 259200)

    async def update_participant_sum_and_handicap_score_in_redis(self, participant):
        keys_pattern = f'participant:{participant.id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)

        sum_score = 0
        for key in keys:
            score = await sync_to_async(redis_client.get)(key)
            sum_score += int(score)

        handicap_score = sum_score - participant.club_member.user.handicap
        redis_key = f'participant:{participant.id}'
        await sync_to_async(redis_client.hset)(redis_key, "sum_score", sum_score)
        await sync_to_async(redis_client.hset)(redis_key, "handicap_score", handicap_score)

        await self.update_rankings_in_redis()

    async def update_rankings_in_redis(self):
        participants = await self.get_participants_from_redis()

        sorted_by_sum_score = sorted(participants, key=lambda p: p.sum_score)
        sorted_by_handicap_score = sorted(participants, key=lambda p: p.handicap_score)

        self.assign_ranks(sorted_by_sum_score, 'sum_rank')
        self.assign_ranks(sorted_by_handicap_score, 'handicap_rank')

        for participant in participants:
            redis_key = f'participant:{participant.id}'
            await sync_to_async(redis_client.hset)(redis_key, "rank", participant.rank)
            await sync_to_async(redis_client.hset)(redis_key, "handicap_rank", participant.handicap_rank)

    async def get_participants_from_redis(self):
        participant_ids = await self.get_participant_ids_from_redis()
        participants = []
        for participant_id in participant_ids:
            sum_score = await sync_to_async(redis_client.hget)(f'participant:{participant_id}', 'sum_score')
            handicap_score = await sync_to_async(redis_client.hget)(f'participant:{participant_id}', 'handicap_score')

            participant = Participant(
                id=participant_id,
                sum_score=int(sum_score),
                handicap_score=int(handicap_score)
            )
            participants.append(participant)

        return participants
