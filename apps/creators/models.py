from decimal import Decimal
from typing import ClassVar

from encrypted_fields.fields import EncryptedEmailField

from django.db import models, transaction
from django.core.validators import MaxLengthValidator, MinLengthValidator

from apps.subscriptions.choices import SubscriptionType

from utils.constants import ZERO
from utils.models import UUIDModel, TimestampedModel

from .choices import Blockchain
from .exceptions import AccountSuspensionError, InsufficientBalanceError


class Creator(UUIDModel, TimestampedModel, models.Model):
    address = models.CharField(
        'address',
        unique=True,
        blank=False,
        max_length=44,
        validators=[MinLengthValidator(32), MaxLengthValidator(44)],
    )
    bio = models.CharField('bio', max_length=200, default='')
    email = EncryptedEmailField('email', unique=True, blank=True, default='')
    social_links = models.JSONField('socials', default=dict)

    # bonfida name service or user provider name(without .sol suffix)
    moniker = models.TextField('moniker', unique=True, blank=True, default='')

    is_suspended = models.BooleanField('is suspended', blank=True, default=False)
    suspension_reason = models.TextField('suspension reason', default='')

    subscription_type = models.CharField(
        'subscription type',
        blank=True,
        max_length=8,
        choices=SubscriptionType.choices,
    )

    is_verified = models.BooleanField('is verified', default=False)

    def __str__(self):
        return self.address

    @property
    def display_name(self) -> str:
        return self.moniker or self.address


class Wallet(UUIDModel, TimestampedModel, models.Model):
    creator = models.OneToOneField(
        to=Creator,
        related_name='wallet',
        verbose_name='creator',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    balance = models.DecimalField('balance', max_digits=20, decimal_places=2, default=ZERO)
    provider_id = models.CharField('circle provider identifier', unique=True, max_length=100, blank=False)

    def __str__(self):
        return str(self.balance)

    @transaction.atomic()
    def top_up(self, amount: Decimal):
        if self.creator.is_suspended:
            raise AccountSuspensionError(self.creator.suspension_reason)

        self.balance = models.F('balance') + amount
        self.save()

    @transaction.atomic()
    def withdraw(self, amount: Decimal):
        if self.creator.is_suspended:
            raise AccountSuspensionError(self.creator.suspension_reason)

        if self.balance - amount < ZERO:
            raise InsufficientBalanceError(f'Your balance is {self.balance} while attempting to withdraw {amount}')

        self.balance = models.F('balance') - amount
        self.save()

    @transaction.atomic()
    def transfer(self, amount: Decimal, recipient: 'Wallet'):
        if self.creator.is_suspended:
            raise AccountSuspensionError(self.creator.suspension_reason)

        if self.balance - amount < ZERO:
            raise InsufficientBalanceError(f'Your balance is {self.balance} while attempting to transfer {amount}')

        self.balance = models.F('balance') - amount
        recipient.balance = models.F('balance') + amount

        self.save()
        recipient.save()


class WalletDepositAddress(UUIDModel, TimestampedModel, models.Model):
    wallet = models.ForeignKey(
        to=Wallet,
        related_name='deposit_addresses',
        on_delete=models.CASCADE,
        verbose_name='wallet',
        db_index=False,
        blank=False,
    )
    address = models.CharField('address', unique=True, max_length=200, blank=False)
    blockchain = models.CharField('blockchain', max_length=100, choices=Blockchain.choices, blank=False)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=('address', 'wallet', 'blockchain'),
                name='wallet_address_and_chain_unique',
            ),
        ]

    def __str__(self):
        return self.address
