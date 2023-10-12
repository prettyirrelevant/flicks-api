from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from apps.creators.serializers import MinimalCreatorSerializer

from .choices import MediaType
from .models import Media, Comment, Content, Livestream


class PreSignedURLSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=50)
    file_type = serializers.ChoiceField(choices=MediaType.choices)


class PreSignedURLListSerializer(serializers.Serializer):
    files = PreSignedURLSerializer(required=True, many=True)

    def validate_files(self, value):  # noqa: PLR6301
        if len(value) > settings.MAX_FILE_UPLOAD_PER_REQUEST:
            raise serializers.ValidationError('Max file upload per request exceeded')

        return value


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


class CommentSerializer(serializers.ModelSerializer):
    author = MinimalCreatorSerializer()

    class Meta:
        model = Comment
        fields = ('id', 'author', 'message', 'created_at', 'updated_at')
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')

    def create(self, validated_data):
        return Comment.objects.create(
            content=self.context['content'],
            message=validated_data['message'],
            author=self.context['request'].user,
        )


class ContentSerializer(serializers.ModelSerializer):
    account = MinimalCreatorSerializer()
    comments = CommentSerializer(many=True)
    media = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()

    def get_media(self, obj):  # noqa: PLR6301
        qs = obj.media.all()
        return MediaSerializer(qs, many=True).data

    def get_likes_count(self, obj):  # noqa: PLR6301
        return obj.likes.count()

    def get_is_liked(self, obj):
        return obj.likes.filter(id=self.context['request'].user.id).exists()

    class Meta:
        model = Content
        fields = (
            'id',
            'account',
            'caption',
            'media',
            'comments',
            'is_liked',
            'likes_count',
            'created_at',
            'updated_at',
        )


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
