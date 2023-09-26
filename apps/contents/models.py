from django.db import models

from utils.models import UUIDModel, TimestampedModel

from .choices import MediaType, MediaUploadStatus


class Content(UUIDModel, TimestampedModel, models.Model):
    account = models.ForeignKey(
        to='accounts.Account',
        verbose_name='account',
        on_delete=models.CASCADE,
        related_name='contents',
        blank=False,
    )
    caption = models.TextField(verbose_name="content caption")


class Media(UUIDModel, TimestampedModel, models.Model):
    content = models.ForeignKey(
        to=Content,
        on_delete=models.CASCADE,
        verbose_name='content',
        related_name='media',
        blank=False
    )
    s3_key = models.CharField(max_length=100, blank=False, verbose_name="file path on s3")
    media_type = models.CharField(max_length=20, choices=MediaType.choices, blank=False, verbose_name="media type")
