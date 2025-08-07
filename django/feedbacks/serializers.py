from rest_framework import serializers
from .models import Feedback

class FeedbackSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(source='author.id', read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'author_id', 'message', 'created_at']