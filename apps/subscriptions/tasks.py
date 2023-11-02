import logging
from datetime import timedelta

from huey import crontab
from huey.contrib.djhuey import lock_task, db_periodic_task

from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from apps.transactions.models import Transaction

from services.sharingan import SharinganService

from .choices import SubscriptionType, SubscriptionDetailStatus
from .models import NFTSubscription, FreeSubscription, SubscriptionDetail, MonetarySubscription

logger = logging.getLogger(__name__)
sharingan_service = SharinganService(settings.SHARINGAN_BASE_URL)


@db_periodic_task(crontab(minute='*/10'))
@lock_task('nft-subscriptions-renewal-check-lock')
def nft_subscriptions_renewal_check():
    nft_subscription_content_type = ContentType.objects.get_for_model(NFTSubscription)
    subscription_details = SubscriptionDetail.objects.filter(
        status=SubscriptionDetailStatus.ACTIVE,
        subscription_type=nft_subscription_content_type,
    )
    for detail in subscription_details:
        an_hour_from_now = timezone.now() + timedelta(hours=1)
        five_minutes_from_now = timezone.now() + timedelta(minutes=5)
        thirty_minutes_from_now = timezone.now() + timedelta(minutes=30)

        if (
            (thirty_minutes_from_now < detail.expires_at <= an_hour_from_now)
            or (five_minutes_from_now < detail.expires_at <= thirty_minutes_from_now)
            or (detail.expires_at <= five_minutes_from_now)
        ):
            is_last_interval = detail.expires_at <= five_minutes_from_now
            process_subscription_detail_renewal(detail, is_last_interval)


@db_periodic_task(crontab(minute='*/10'))
@lock_task('monetary-subscriptions-renewal-check-lock')
def monetary_subscriptions_renewal_check():
    try:
        monetary_subscription_content_type = ContentType.objects.get_for_model(MonetarySubscription)
        subscription_details = SubscriptionDetail.objects.filter(
            status=SubscriptionDetailStatus.ACTIVE,
            subscription_type=monetary_subscription_content_type,
        )
        for detail in subscription_details:
            one_day_from_now = timezone.now() + timedelta(days=1)
            two_days_from_now = timezone.now() + timedelta(days=2)
            three_days_from_now = timezone.now() + timedelta(days=3)
            five_minutes_from_now = timezone.now() + timedelta(minutes=5)

            if (
                (two_days_from_now < detail.expires_at <= three_days_from_now)
                or (one_day_from_now < detail.expires_at <= two_days_from_now)
                or (five_minutes_from_now < detail.expires_at <= one_day_from_now)
            ):
                is_last_interval = detail.expires_at <= five_minutes_from_now
                process_subscription_detail_renewal(detail, is_last_interval)

    except Exception:
        logger.exception('An error occurred in monetary_subscriptions_renewal_check')


def process_subscription_detail_renewal(
    instance,
    is_last_interval=False,  # noqa: FBT002
):
    # The current subscription might have changed since the last time the subscriber renewed. We need to check that.
    if instance.creator.subscription_type == SubscriptionType.FREE:
        subscription = FreeSubscription.objects.get(created_by=instance.creator)

        instance.expires_at += timedelta(weeks=520)
        instance.subscription_object = subscription
        instance.status = SubscriptionDetailStatus.ACTIVE
        instance.save()

    elif instance.creator.subscription_type == SubscriptionType.NFT:
        subscription = NFTSubscription.objects.get(creator=instance.creator)
        response = sharingan_service.has_nft_in_collection(
            user_address=instance.subscriber.address,
            collection_name=subscription.collection_name,
        )
        if response is None and is_last_interval:
            instance.status = SubscriptionDetailStatus.EXPIRED
            instance.save()

        instance.expires_at += timedelta(days=1)
        instance.subscription_object = subscription
        instance.status = SubscriptionDetailStatus.ACTIVE
        instance.save()

    elif instance.creator.subscription_type == SubscriptionType.MONETARY:
        subscription = MonetarySubscription.objects.get(creator=instance.creator)
        if instance.subscriber.wallet.balance < subscription.amount and is_last_interval:
            logger.warning('Insufficient balance for subscription instance %s', instance.id)

            instance.status = SubscriptionDetailStatus.EXPIRED
            instance.save()
            return

        instance.subscriber.wallet.transfer(amount=subscription.amount, recipient=instance.creator.wallet)
        Transaction.create_subscription(
            creator=instance.creator,
            subscriber=instance.subscriber,
            amount=instance.monetary_subscription.amount,
        )

        instance.expires_at += timedelta(days=30)
        instance.subscription_object = subscription
        instance.status = SubscriptionDetailStatus.ACTIVE
        instance.save()
