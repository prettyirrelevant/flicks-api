import datetime

import boto3

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings

from utils.models import UUIDModel, TimestampedModel

from .choices import MediaType


class Content(UUIDModel, TimestampedModel, models.Model):
    account = models.ForeignKey(
        to='accounts.Account',
        verbose_name='account',
        on_delete=models.CASCADE,
        related_name='contents',
        blank=False,
    )
    caption = models.TextField(verbose_name='content caption')

    def __str__(self):
        return f'{self.account.address} - {self.caption}'


class Media(UUIDModel, TimestampedModel, models.Model):
    content = models.ForeignKey(
        to=Content,
        on_delete=models.CASCADE,
        verbose_name='content',
        related_name='media',
        blank=False,
    )
    s3_key = models.CharField(max_length=100, blank=False, verbose_name='file path on s3')
    media_type = models.CharField(max_length=20, choices=MediaType.choices, blank=False, verbose_name='media type')

    def __str__(self):
        return f'{self.media_type} - {self.s3_key}'

    @property
    def url(self):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.BUCKET_NAME, 'Key': self.s3_key},
            ExpiresIn=settings.PRESIGNED_URL_EXPIRATION,
        )


class Livestream(UUIDModel, TimestampedModel, models.Model):
    account = models.ForeignKey(
        to='accounts.Account',
        verbose_name='account',
        on_delete=models.CASCADE,
        related_name='livestream',
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
        return f"Livestream: {self.title}"
