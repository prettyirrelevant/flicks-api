from django.db import models


class MediaType(models.TextChoices):
    IMAGE = 'image'
    VIDEO = 'video'


class MediaUploadStatus(models.TextChoices):
    IN_PROGRESS = 'in progress'
    COMPLETED = 'completed'
