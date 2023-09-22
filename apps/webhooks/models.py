from django.db import models

from utils.models import UUIDModel, TimestampedModel


class WebhookStatus(models.TextChoices):
    PENDING = 'pending'
    COMPLETED = 'completed'


class WebhookType(models.TextChoices):
    TRANSFERS = 'transfers'
    SUBSCRIPTION_CONFIRMATION = 'subscription confirmation'


class Webhook(UUIDModel, TimestampedModel, models.Model):
    payload = models.JSONField('payload', blank=False)
    message_id = models.CharField('message identifier', unique=True, max_length=100, blank=False)
    status = models.CharField('status', max_length=10, choices=WebhookStatus.choices, blank=False)
    notification_type = models.CharField('notification type', max_length=50, choices=WebhookType.choices, blank=False)

    def __str__(self):
        return str(self.id)
