from rest_framework import serializers
from .models import ClubMember


# TODO:ClubMember와 Member 매핑해서 이름, 이미지 url, handicap 가져오기!
class ClubMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubMember
        fields = '__all__'
