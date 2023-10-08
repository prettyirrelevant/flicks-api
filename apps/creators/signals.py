from django.conf import settings
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save

from apps.subscriptions.models import FreeSubscription
from apps.subscriptions.choices import SubscriptionStatus

from services.circle import CircleAPI

from .models import Wallet, Creator
from .tasks import create_deposit_addresses_for_wallet

circle_api = CircleAPI(
    api_key=settings.CIRCLE_API_KEY,
    base_url=settings.CIRCLE_API_BASE_URL,
)


@receiver(post_save, sender=Creator)
def create_profile_and_subscription(sender, instance, created, **kwargs):  # noqa: ARG001
    if not created:
        return

    with transaction.atomic():
        FreeSubscription.objects.create(
            creator=instance,
            status=SubscriptionStatus.ACTIVE,
        )

        response = circle_api.create_wallet(idempotency_key=instance.id, address=instance.address)
        if response is None:
            raise Exception(  # noqa: TRY002  # pylint: disable=broad-exception-raised
                f'Unable to create a wallet for {instance.address}',
            )

        wallet = Wallet.objects.create(
            account=instance,
            provider_id=response['data']['walletId'],
        )
        create_deposit_addresses_for_wallet.schedule((wallet.id,), delay=1)
