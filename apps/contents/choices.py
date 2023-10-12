from django.db import models


class MediaType(models.TextChoices):
    IMAGE = 'image'
    VIDEO = 'video'


class ContentType(models.TextChoices):
    FREE = 'free'
    PAID = 'paid'
