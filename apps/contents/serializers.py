from rest_framework import serializers

from .choices import MediaType


class PreSignedURLSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=50)
    file_type = serializers.ChoiceField(choices=MediaType.choices)

    def create(self, validated_data):
        ...

    def update(self, instance, validated_data):
        ...
