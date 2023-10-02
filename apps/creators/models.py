from decimal import Decimal
from typing import ClassVar

from django.db import models, transaction
from django.core.validators import MaxLengthValidator, MinLengthValidator

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
    email = models.EmailField('email', unique=True, blank=True, default='')

    # Preference of moniker in descending order
    # 1. Bonfida Name Service or SNS
    # 2. User provided moniker without the .sol suffix
    # 3. Creator address.
    moniker = models.CharField('moniker', max_length=250, blank=True, default='')

    is_suspended = models.BooleanField('is suspended', blank=True, default=False)
    suspension_reason = models.TextField('suspension reason', default='')

    is_verified = models.BooleanField('is verified', blank=True, default=False)

    def __str__(self):
        return self.address


class Wallet(UUIDModel, TimestampedModel, models.Model):
    account = models.OneToOneField(
        to=Creator,
        related_name='wallet',
        verbose_name='account',
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
        if self.account.is_suspended:
            raise AccountSuspensionError(self.account.suspension_reason)

        self.balance = models.F('balance') + amount
        self.save()

    @transaction.atomic()
    def withdraw(self, amount: Decimal):
        if self.account.is_suspended:
            raise AccountSuspensionError(self.account.suspension_reason)

        if self.balance - amount < ZERO:
            raise InsufficientBalanceError(f'Your balance is {self.balance} while attempting to withdraw {amount}')

        self.balance = models.F('balance') - amount
        self.save()

    @transaction.atomic()
    def transfer(self, amount: Decimal, recipient: 'Wallet'):
        if self.account.is_suspended:
            raise AccountSuspensionError(self.account.suspension_reason)

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