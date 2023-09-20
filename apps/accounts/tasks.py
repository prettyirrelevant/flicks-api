from huey.contrib.djhuey import db_task

from django.conf import settings
from django.db import transaction

from services.circle import CircleAPI

from .choices import Blockchain
from .models import Wallet, WalletDepositAddress

circle_api = CircleAPI(
    api_key=settings.CIRCLE_API_KEY,
    base_url=settings.CIRCLE_API_BASE_URL,
)


@db_task()
def create_deposit_addresses_for_wallet(wallet_id):
    with transaction.atomic():
        wallet = Wallet.objects.get(id=wallet_id)
        for blockchain in Blockchain:
            if wallet.deposit_addresses.filter(blockchain=blockchain).exists():
                continue

            response = circle_api.create_address_for_wallet(wallet_id=wallet.provider_id, chain=blockchain.value)
            if response is None:
                raise Exception(  # noqa: TRY002  # pylint: disable=broad-exception-raised
                    f'Unable to create {blockchain.value} address for wallet {wallet.account.address}',
                )

            WalletDepositAddress.objects.create(
                wallet=wallet,
                blockchain=blockchain,
                address=response['data']['address'],
            )
