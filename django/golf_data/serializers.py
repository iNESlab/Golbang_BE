'''
MVP demo ver 0.0.3
2025.03.15
golf_data/serializers.py

역할:
- GolfClub, GolfCourse, Tee 모델의 데이터를 API 응답 형태에 맞게 직렬화하기 위한 파일
'''

from rest_framework import serializers
from .models import GolfClub, GolfCourse, Tee

'''
공통 골프 코스 시리얼라이저
'''
class GolfCourseBaseSerializer(serializers.ModelSerializer):
    golf_course_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    golf_course_name = serializers.CharField(source='course_name', read_only=True)

    class Meta:
        model = GolfCourse
        fields = ['golf_course_id', 'golf_course_name', 'holes', 'par']

'''
공통 골프 클럽 시리얼라이저
'''
class GolfClubBaseSerializer(serializers.ModelSerializer):
    golf_club_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    golf_club_name = serializers.CharField(source='club_name', read_only=True)

    class Meta:
        model = GolfClub
        fields = ['golf_club_id', 'golf_club_name', 'address', 'longitude', 'latitude']

'''
전체 골프 클럼 리스트 조회 시리얼라이저
'''
class GolfClubListSerializer(GolfClubBaseSerializer):
    courses = GolfCourseBaseSerializer(many=True, read_only=True)

    class Meta(GolfClubBaseSerializer.Meta):
        fields = GolfClubBaseSerializer.Meta.fields + ['courses']


'''
특정 골프장 상세 조회 시리얼라이저
'''
class TeeSerializer(serializers.ModelSerializer):
    hole_pars = serializers.SerializerMethodField()
    hole_handicaps = serializers.SerializerMethodField()

    class Meta:
        model = Tee
        fields = ['tee_name', 'hole_pars', 'hole_handicaps']

    def get_hole_pars(self, obj):
        return [getattr(obj, f'hole_{i}_par', None) for i in range(1, 19)]

    def get_hole_handicaps(self, obj):
        return [getattr(obj, f'hole_{i}_handicap', None) for i in range(1, 19)]


class GolfCourseDetailSerializer(GolfCourseBaseSerializer):
    tees = TeeSerializer(many=True, read_only=True)

    class Meta(GolfCourseBaseSerializer.Meta):
        fields = GolfCourseBaseSerializer.Meta.fields + ['tees']


class GolfClubDetailSerializer(GolfClubBaseSerializer):
    courses = GolfCourseDetailSerializer(many=True, read_only=True)

    class Meta(GolfClubBaseSerializer.Meta):
        fields = GolfClubBaseSerializer.Meta.fields + ['courses']
