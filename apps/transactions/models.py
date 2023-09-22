from django.db import models

from utils.models import UUIDModel, TimestampedModel

from .choices import TransactionType, TransactionStatus


class Transaction(UUIDModel, TimestampedModel, models.Model):
    account = models.ForeignKey(
        to='accounts.Account',
        verbose_name='account',
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True,
        blank=True,
    )
    metadata = models.JSONField('metadata', default=dict)
    narration = models.TextField('narration', blank=True, default='')
    amount = models.DecimalField('amount', max_digits=20, decimal_places=6, blank=False)
    reference = models.CharField('transaction reference', unique=True, max_length=200, blank=False)
    status = models.CharField('status', max_length=10, choices=TransactionStatus.choices, blank=False)
    tx_type = models.CharField('transaction type', max_length=30, choices=TransactionType.choices, blank=False)

    def __str__(self):
        return self.id
