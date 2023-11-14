import time
import hashlib
from decimal import Decimal
from typing import ClassVar

from algosdk.constants import ADDRESS_LEN

from django.conf import settings
from django.db import models, transaction
from django.core.validators import MinLengthValidator

from apps.subscriptions.choices import SubscriptionType

from utils.constants import ZERO, NONCE_DURATION
from utils.models import UUIDModel, TimestampedModel

from .choices import Blockchain
from .exceptions import AccountSuspensionError, InsufficientBalanceError


class Creator(UUIDModel, TimestampedModel, models.Model):
    address = models.CharField(
        'address',
        unique=True,
        blank=False,
        max_length=ADDRESS_LEN,
        validators=[MinLengthValidator(ADDRESS_LEN)],
    )
    bio = models.CharField('bio', max_length=200, default='')
    image_url = models.URLField('image url', blank=False)
    banner_url = models.URLField('banner url', blank=False)
    social_links = models.JSONField('socials', default=dict)

    # NFDomains name or user provider name(without .algo suffix)
    moniker = models.TextField('moniker', unique=True, blank=False)

    is_suspended = models.BooleanField('is suspended', blank=True, default=False)
    suspension_reason = models.TextField('suspension reason', default='')

    subscription_type = models.CharField(
        'subscription type',
        null=False,
        blank=False,
        max_length=13,
        choices=SubscriptionType.choices,
    )

    is_verified = models.BooleanField('is verified', default=False)

    def __str__(self):
        return self.address

    @property
    def display_name(self) -> str:
        return self.moniker or self.address


class WalletAuthenticationRecord(UUIDModel, TimestampedModel, models.Model):
    creator = models.ForeignKey(
        Creator,
        null=True,
        on_delete=models.SET_NULL,
        related_name='wallet_authentication_records',
    )
    nonce = models.CharField('nonce', max_length=100, blank=False, unique=True)
    transaction_reference = models.CharField('transaction reference', max_length=200, blank=False, unique=True)

    @staticmethod
    def generate_nonce() -> str:
        timestamp = int(time.time() * 1000)
        # this is totally fine for now
        hash_digest = hashlib.sha256(f'{timestamp}:{settings.SECRET_KEY}'.encode()).hexdigest()
        return f'FLICKS:{timestamp}:{hash_digest}'

    @staticmethod
    def validate_nonce(nonce: str) -> bool:
        if not nonce.startswith('FLICKS'):
            return False

        parts = nonce[7:].split(':')
        if len(parts) != 2:  # noqa: PLR2004
            return False

        timestamp, nonce_hash = parts

        try:
            regenerated_hash = hashlib.sha256(f'{timestamp}:{settings.SECRET_KEY}'.encode()).hexdigest()
        except Exception:  # noqa: BLE001
            return False

        return nonce_hash == regenerated_hash and int(time.time() * 1000) - int(timestamp) <= NONCE_DURATION


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

        self.refresh_from_db()

    @transaction.atomic()
    def withdraw(self, amount: Decimal):
        if self.creator.is_suspended:
            raise AccountSuspensionError(self.creator.suspension_reason)

        if self.balance - amount < ZERO:
            raise InsufficientBalanceError(f'Your balance is {self.balance} while attempting to withdraw {amount}')

        self.balance = models.F('balance') - amount
        self.save()

        self.refresh_from_db()

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

        self.refresh_from_db()
        recipient.refresh_from_db()


class WalletDepositAddress(UUIDModel, TimestampedModel, models.Model):
    wallet = models.ForeignKey(
        to=Wallet,
        related_name='deposit_addresses',
        on_delete=models.CASCADE,
        verbose_name='wallet',
        db_index=False,
        blank=False,
    )
    address = models.CharField('address', max_length=200, blank=False)
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
