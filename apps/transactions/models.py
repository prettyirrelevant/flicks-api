from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db import models, transaction

from utils.models import UUIDModel, TimestampedModel

from .choices import TransactionType, TransactionStatus

if TYPE_CHECKING:
    from apps.creators.models import Creator


class Transaction(UUIDModel, TimestampedModel, models.Model):
    account = models.ForeignKey(
        to='creators.Creator',
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

    @classmethod
    @transaction.atomic()
    def create_subscription(cls, amount: Decimal, creator: 'Creator', subscriber: 'Creator') -> None:
        creator_tx = cls(
            amount=amount,
            account=creator,
            tx_type=TransactionType.CREDIT,
            status=TransactionStatus.SUCCESSFUL,
            narration=f'@{subscriber.moniker} just paid {amount} USD for subscription',
        )
        subscriber_tx = cls(
            amount=amount,
            account=subscriber,
            tx_type=TransactionType.DEBIT,
            status=TransactionStatus.SUCCESSFUL,
            narration=f'You just paid {amount} USD to subscribe to @{creator.moniker}',
        )

        cls.objects.bulk_create([creator_tx, subscriber_tx])

    @classmethod
    @transaction.atomic()
    def create_payment_for_content(cls, amount: Decimal, creator: 'Creator', subscriber: 'Creator'):
        creator_tx = cls(
            amount=amount,
            account=creator,
            tx_type=TransactionType.CREDIT,
            status=TransactionStatus.SUCCESSFUL,
            narration=f'@{subscriber.moniker} just paid {amount} USD for your content',
        )
        subscriber_tx = cls(
            amount=amount,
            account=subscriber,
            tx_type=TransactionType.DEBIT,
            status=TransactionStatus.SUCCESSFUL,
            narration=f'You just paid {amount} USD to view a content from @{creator.moniker}',
        )

        cls.objects.bulk_create([creator_tx, subscriber_tx])

    @classmethod
    @transaction.atomic()
    def create_withdrawal(cls, creator: 'Creator', amount: Decimal, metadata: dict[str, Any]):
        cls.objects.create(
            amount=amount,
            account=creator,
            metadata=metadata,
            tx_type=TransactionType.DEBIT,
            status=TransactionStatus.PENDING,
            narration=f'You just withdrew {amount} USD from your wallet',
        )
