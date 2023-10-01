from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from .choices import MediaType
from .models import Media, Content, Livestream


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
        fields = ('s3_key', 'media_type', 'url', 'blur_hash')
        read_only_fields = ('url',)


class CreateContentSerializer(serializers.Serializer):
    caption = serializers.CharField()
    media = serializers.ListField(
        child=MediaSerializer(),
        allow_empty=False,
        max_length=settings.MAX_FILE_UPLOAD_PER_REQUEST,
    )

    def create(self, validated_data):
        account = self.context['request'].user
        with transaction.atomic():
            content = Content.objects.create(account=account, caption=validated_data['caption'])
            for media in validated_data['media']:
                Media.objects.create(
                    content=content,
                    media_type=media['media_type'],
                    s3_key=media['s3_key'],
                )
            return content

    def update(self, instance, validated_data):
        ...


class UpdateContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ('caption',)


class ContentSerializer(serializers.ModelSerializer):
    media = serializers.SerializerMethodField()

    def get_media(self, obj):  # noqa: PLR6301
        qs = obj.media.all()
        return MediaSerializer(qs, many=True).data

    class Meta:
        model = Content
        fields = ('id', 'caption', 'media', 'created_at', 'updated_at')


class LiveStreamSerializer(serializers.ModelSerializer):
    start = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        now = timezone.now()
        if attrs.get('start', None) is None:
            attrs['start'] = now  # instant livestream
        if attrs['start'] < now:
            raise serializers.ValidationError(detail={'start': 'invalid start time'})
        attrs['account'] = self.context['request'].user
        return attrs

    class Meta:
        model = Livestream
        fields = ('id', 'account', 'title', 'description', 'start', 'duration')
        read_only_fields = ('id', 'account')
