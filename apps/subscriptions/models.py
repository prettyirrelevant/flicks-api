from typing import ClassVar

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from apps.subscriptions.choices import SubscriptionStatus, SubscriptionDetailStatus

from utils.models import UUIDModel, TimestampedModel


class FreeSubscription(UUIDModel, TimestampedModel, models.Model):
    creator = models.ForeignKey(
        to='creators.Creator',
        related_name='free_subscriptions',
        verbose_name='creator',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    status = models.CharField('status', max_length=10, choices=SubscriptionStatus.choices, blank=False)


class TokenGatedSubscription(UUIDModel, TimestampedModel, models.Model):
    creator = models.ForeignKey(
        to='creators.Creator',
        related_name='token_gated_subscriptions',
        verbose_name='creator',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    token_name = models.TextField('token name', blank=False)
    token_decimals = models.IntegerField('token decimals', blank=False)
    token_id = models.CharField('token identifier', max_length=100, blank=False)
    minimum_token_balance = models.DecimalField('minimum token balance', blank=False, max_digits=20, decimal_places=2)

    status = models.CharField('status', max_length=10, choices=SubscriptionStatus.choices, blank=False)


# class NFTSubscription(UUIDModel, TimestampedModel, models.Model):
#     creator = models.ForeignKey(
#         to='creators.Creator',
#         related_name='nft_subscriptions',
#         verbose_name='creator',
#         on_delete=models.SET_NULL,
#         blank=True,
#         null=True,
#     )
#
#     collection_name = models.TextField('collection name', blank=False)
#     collection_image_url = models.TextField('collection image url', blank=False)
#     collection_description = models.TextField('collection description', blank=False)
#     collection_address = models.CharField('collection address', max_length=44, blank=False)
#
#     status = models.CharField('status', max_length=10, choices=SubscriptionStatus.choices, blank=False)


class MonetarySubscription(UUIDModel, TimestampedModel, models.Model):
    creator = models.ForeignKey(
        to='creators.Creator',
        related_name='monetary_subscriptions',
        verbose_name='creator',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    amount = models.DecimalField('amount', max_digits=20, decimal_places=2, blank=False)
    status = models.CharField('status', max_length=10, choices=SubscriptionStatus.choices, blank=False)


class SubscriptionDetail(UUIDModel, TimestampedModel, models.Model):
    """Subscription detail model.

    Monetary subscriptions are issued a monthly subscription detail.
    --> A background job checks two days to expiry and tries to notify the user via email if the balance is low.
    --> A background job extends the subscription by a month if the user has sufficient balance a day before expiry.
    --> If renewal happens while subscription is active, a month is added to `expires_at`.
        Otherwise, add a month to the current datetime.

    # NFT subscriptions are issued a daily subscription detail.
    # --> A background job checks 15 minutes to expiry and tries to renew the subscription.
    # --> If renewal happens while subscription is active, a day is added to `expires_at`.
    #     Otherwise, add a day to the current datetime.

    Token gated subscriptions are issued a daily subscription detail.
    --> A background job checks 15 minutes to expiry and tries to renew the subscription.
    --> If renewal happens while subscription is active, a day is added to `expires_at`.
        Otherwise, add a day to the current datetime.


    Free subscriptions are issued a 10yrs subscription detail (it can be cancelled at any point).
    """

    creator = models.ForeignKey(
        blank=False,
        db_index=True,
        to='creators.Creator',
        verbose_name='creator',
        on_delete=models.CASCADE,
        related_name='subscribers',
    )
    subscriber = models.ForeignKey(
        blank=False,
        db_index=True,
        to='creators.Creator',
        verbose_name='subscriber',
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )

    # generic foreign key relationships for subscriptions
    subscription_id = models.UUIDField('subscription id', blank=False)
    subscription_type = models.ForeignKey(
        to=ContentType,
        related_name='+',
        on_delete=models.CASCADE,
        verbose_name='subscription type',
    )
    subscription_object = GenericForeignKey(ct_field='subscription_type', fk_field='subscription_id')

    expires_at = models.DateTimeField('expires at', blank=False)
    status = models.CharField('status', max_length=10, choices=SubscriptionDetailStatus.choices, blank=False)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=('creator', 'subscriber'), name='creator_subscriber_unique'),
        ]
