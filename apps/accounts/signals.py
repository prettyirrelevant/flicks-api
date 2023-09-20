from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save

from services.circle import CircleAPI

from .models import Wallet, Account
from .tasks import create_deposit_addresses_for_wallet

circle_api = CircleAPI(
    api_key=settings.CIRCLE_API_KEY,
    base_url=settings.CIRCLE_API_BASE_URL,
)


@receiver(post_save, sender=Account)
def create_profile(sender, instance, created, **kwargs):  # noqa: ARG001
    if not created:
        return

    response = circle_api.create_wallet(idempotency_key=instance.id, address=instance.address)
    if response is None:
        raise Exception(  # noqa: TRY002  # pylint: disable=broad-exception-raised
            f'Unable to create a wallet for {instance.address}',
        )

    wallet = Wallet.objects.create(
        account=instance,
        provider_id=response['data']['1016758320'],
    )
    create_deposit_addresses_for_wallet.schedule((wallet.id,), delay=1)
