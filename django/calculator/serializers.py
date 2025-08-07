from rest_framework import serializers

class FileUploadSerializer(serializers.Serializer):
    upload_file = serializers.FileField()
    selected_holes = serializers.CharField(required=True)
