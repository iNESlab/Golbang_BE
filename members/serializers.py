from rest_framework import serializers
from .models import Member


# TODO:Member와 Member 매핑해서 이름, 이미지 url, handicap 가져오기!
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'
