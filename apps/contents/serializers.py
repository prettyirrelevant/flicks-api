from rest_framework import serializers
from .models import Media, Content
from django.conf import settings
from .choices import MediaType
from django.db import transaction


class PreSignedURLSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=50)
    file_type = serializers.ChoiceField(choices=MediaType.choices)

    def create(self, validated_data):
        ...

    def update(self, instance, validated_data):
        ...


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ("s3_key", "media_type")


class CreateContentSerializer(serializers.Serializer):
    caption = serializers.CharField()
    media = serializers.ListField(child=MediaSerializer(), allow_empty=False, max_length=settings.MAX_FILE_UPLOAD_PER_REQUEST)

    def create(self, validated_data):
        account = self.context['request'].user
        content = None
        with transaction.atomic():
            content = Content.objects.create(account=account, caption=validated_data["caption"])
            for media in validated_data['media']:
                Media.objects.create(
                    content=content,
                    media_type=media['media_type'],
                    s3_key=media['s3_key']
                )
        return content
