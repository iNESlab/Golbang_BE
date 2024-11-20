'''
MVP demo ver 0.0.2
2024.10.31
golf_data/serializers.py

역할:
- GolfClub, GolfCourse, Tee 모델의 데이터를 API 응답 형태에 맞게 직렬화하기 위한 파일
'''

from rest_framework import serializers
from .models import GolfClub, GolfCourse, Tee

class TeeSerializer(serializers.ModelSerializer):
    hole_pars = serializers.SerializerMethodField()
    hole_handicaps = serializers.SerializerMethodField()

    class Meta:
        model = Tee
        fields = ['hole_pars', 'hole_handicaps']

    def get_hole_pars(self, obj):
        # 각 홀의 Par 정보를 리스트로 반환
        return [getattr(obj, f'hole_{i}_par') for i in range(1, 19)]

    def get_hole_handicaps(self, obj):
        # 각 홀의 Handicap 정보를 리스트로 반환
        return [getattr(obj, f'hole_{i}_handicap') for i in range(1, 19)]

class GolfCourseSerializer(serializers.ModelSerializer):
    hole_pars = serializers.SerializerMethodField()
    hole_handicaps = serializers.SerializerMethodField()

    class Meta:
        model = GolfCourse
        fields = ['course_name', 'holes', 'par', 'hole_pars', 'hole_handicaps']

    def get_hole_pars(self, obj):
        # Tee 정보는 한 개만 있다고 가정하고 첫 번째 Tee의 hole_pars 가져오기
        tee = obj.tees.first()
        return [getattr(tee, f'hole_{i}_par') for i in range(1, 19)] if tee else []

    def get_hole_handicaps(self, obj):
        # Tee 정보는 한 개만 있다고 가정하고 첫 번째 Tee의 hole_handicaps 가져오기
        tee = obj.tees.first()
        return [getattr(tee, f'hole_{i}_handicap') for i in range(1, 19)] if tee else []

class GolfClubSerializer(serializers.ModelSerializer):
    courses = GolfCourseSerializer(many=True, read_only=True)

    class Meta:
        model = GolfClub
        fields = ['club_name', 'address', 'courses']
