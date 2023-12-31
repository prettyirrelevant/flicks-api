from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from apps.creators.serializers import MinimalCreatorSerializer

from utils.constants import ZERO, MINIMUM_ALLOWED_WITHDRAWAL_AMOUNT

from .choices import MediaType, ContentType
from .models import Media, Comment, Content, Livestream


class PreSignedURLSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=50)
    file_type = serializers.ChoiceField(choices=MediaType.choices)


class PreSignedURLListSerializer(serializers.Serializer):
    files = PreSignedURLSerializer(many=True)

    def validate_files(self, value):
        if len(value) > settings.MAX_FILE_UPLOAD_PER_REQUEST:
            raise serializers.ValidationError('Max file upload per request exceeded')

        return value


class MediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        if (
            obj.content.content_type == ContentType.FREE
            or self.context['request'].user == obj.content.creator
            or (
                obj.content.content_type == ContentType.PAID
                and obj.content.purchases.filter(id=self.context['request'].user.id).exists()
            )
        ):
            return obj.url

        return None

    class Meta:
        model = Media
        fields = ('s3_key', 'media_type', 'url', 'created_at', 'updated_at')
        read_only_fields = ('url', 'blur_hash', 'created_at', 'updated_at')


class CreateContentSerializer(serializers.Serializer):
    caption = serializers.CharField()
    price = serializers.DecimalField(max_digits=20, decimal_places=2, default=ZERO)
    content_type = serializers.ChoiceField(choices=ContentType.choices, required=True)
    media = serializers.ListField(
        child=MediaSerializer(),
        allow_empty=False,
        max_length=settings.MAX_FILE_UPLOAD_PER_REQUEST,
    )

    def create(self, validated_data):
        creator = self.context['request'].user
        with transaction.atomic():
            media = validated_data.pop('media')
            content = Content.objects.create(**validated_data, creator=creator)
            for entry in media:
                Media.objects.create(
                    content=content,
                    s3_key=entry['s3_key'],
                    media_type=entry['media_type'],
                )
            return content

    def validate(self, attrs):
        if attrs['content_type'] == ContentType.PAID and attrs['price'] < Decimal('1.00'):
            raise serializers.ValidationError('Content with paywall must have a price of at least $1.00')

        return attrs


class UpdateContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = ('caption',)


class CreateCommentSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=200)

    def create(self, validated_data):
        return Comment.objects.create(
            content=self.context['content'],
            message=validated_data['message'],
            author=self.context['request'].user,
        )


class CommentSerializer(serializers.ModelSerializer):
    author = MinimalCreatorSerializer()

    class Meta:
        model = Comment
        fields = ('id', 'author', 'message', 'created_at', 'updated_at')
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')


class ContentSerializer(serializers.ModelSerializer):
    media = MediaSerializer(many=True)
    creator = MinimalCreatorSerializer()
    comments = CommentSerializer(many=True)
    is_liked = serializers.SerializerMethodField()
    is_purchased = serializers.SerializerMethodField()

    def get_is_liked(self, obj):
        return obj.likes.filter(id=self.context['request'].user.id).exists()

    def get_is_purchased(self, obj):
        return (
            obj.content_type == ContentType.FREE
            or self.context['request'].user == obj.creator
            or obj.purchases.filter(id=self.context['request'].user.id).exists()
        )

    class Meta:
        model = Content
        fields = (
            'id',
            'price',
            'media',
            'creator',
            'caption',
            'comments',
            'is_liked',
            'created_at',
            'updated_at',
            'likes_count',
            'is_purchased',
            'content_type',
            'comments_count',
        )


class LiveStreamSerializer(serializers.ModelSerializer):
    creator = MinimalCreatorSerializer(read_only=True)
    start = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        now = timezone.now()
        if attrs.get('start', None) is None:
            attrs['start'] = now  # instant livestream

        if attrs['start'] < now:
            raise serializers.ValidationError(detail={'start': 'invalid start time'})

        attrs['creator'] = self.context['request'].user
        return attrs

    class Meta:
        model = Livestream
        fields = ('id', 'creator', 'title', 'description', 'start', 'duration')
        read_only_fields = ('id', 'creator')


class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=MINIMUM_ALLOWED_WITHDRAWAL_AMOUNT)

    def validate_amount(self, value):
        if self.context['request'].user.wallet.balance < value:
            raise serializers.ValidationError('Creator balance is too low for this withdrawal')

        return value
