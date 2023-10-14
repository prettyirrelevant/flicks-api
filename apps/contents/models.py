import datetime

from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

from services.s3 import S3Service

from utils.constants import ZERO
from utils.models import UUIDModel, TimestampedModel

from .choices import MediaType, ContentType


class Content(UUIDModel, TimestampedModel, models.Model):
    creator = models.ForeignKey(
        to='creators.Creator',
        verbose_name='creator',
        on_delete=models.CASCADE,
        related_name='contents',
        blank=False,
    )
    caption = models.TextField(verbose_name='content caption')
    likes = models.ManyToManyField(to='creators.Creator', verbose_name='likes', related_name='likes')

    # `price` & `purchases` are only used when the content_type is paid.
    purchases = models.ManyToManyField(to='creators.Creator', related_name='purchased_contents')
    price = models.DecimalField('price', max_digits=20, decimal_places=2, default=ZERO)
    content_type = models.CharField('content type', max_length=4, choices=ContentType.choices, blank=False)

    def __str__(self):
        return f'{self.creator.address} - {self.caption}'

    @property
    def likes_count(self):
        return self.likes.count()

    @property
    def comments_count(self):
        return self.comments.count()


class Media(UUIDModel, TimestampedModel, models.Model):
    content = models.ForeignKey(
        to=Content,
        on_delete=models.CASCADE,
        verbose_name='content',
        related_name='media',
        blank=False,
    )
    blur_hash = models.TextField('media blur hash', default='')
    s3_key = models.CharField(max_length=100, blank=False, verbose_name='file path on s3')
    media_type = models.CharField(max_length=20, choices=MediaType.choices, blank=False, verbose_name='media type')

    def __str__(self):
        return f'{self.media_type} - {self.s3_key}'

    @property
    def url(self):
        s3_service = S3Service(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY, settings.BUCKET_NAME)
        return s3_service.get_pre_signed_fetch_url(self.s3_key, settings.PRESIGNED_URL_EXPIRATION)


class Livestream(UUIDModel, TimestampedModel, models.Model):
    creator = models.ForeignKey(
        to='creators.Creator',
        verbose_name='creator',
        on_delete=models.CASCADE,
        related_name='livestreams',
        blank=False,
    )
    title = models.CharField(max_length=50, blank=False, verbose_name='title')
    description = models.TextField(verbose_name='description')
    start = models.DateTimeField(verbose_name='start timestamp')
    duration = models.DurationField(
        verbose_name='livestream duration',
        validators=[
            MinValueValidator(datetime.timedelta(minutes=10)),
            MaxValueValidator(datetime.timedelta(minutes=30)),
        ],
    )

    def __str__(self):
        return f'Livestream: {self.title}'


class Comment(UUIDModel, TimestampedModel, models.Model):
    content = models.ForeignKey(
        to=Content,
        blank=False,
        verbose_name='content',
        related_name='comments',
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(
        blank=False,
        to='creators.Creator',
        verbose_name='author',
        on_delete=models.CASCADE,
        related_name='my_comments',
    )
    message = models.CharField('message', max_length=200, blank=False)
