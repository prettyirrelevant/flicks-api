from django.db import models
from django.core.validators import MaxLengthValidator, MinLengthValidator

from utils.models import UUIDModel, TimestampedModel


class Account(UUIDModel, TimestampedModel, models.Model):
    address = models.CharField(
        'address',
        unique=True,
        blank=False,
        max_length=44,
        validators=[MinLengthValidator(32), MaxLengthValidator(44)],
    )
    email = models.EmailField('email', unique=True, blank=True, default='')

    # This is populated by checking if the user has the address registered to a name service.
    # Bonfida Name Service, Unstoppable Domains, ENS (added Solana address)
    moniker = models.CharField('moniker', max_length=250, blank=True, default='')

    is_suspended = models.BooleanField('is suspended', blank=True, default=False)
    suspension_reason = models.TextField('suspension reason', default='')

    is_verified = models.BooleanField('is verified', blank=True, default=False)

    def __str__(self):
        return self.address
