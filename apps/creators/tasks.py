from decimal import Decimal

from huey import crontab
from huey.contrib.djhuey import db_task, lock_task, db_periodic_task

from django.conf import settings
from django.db import transaction
from django.db.models import Count

from apps.transactions.models import Transaction
from apps.transactions.choices import TransactionType, TransactionStatus

from services.circle import CircleAPI

from utils.constants import MINIMUM_ALLOWED_DEPOSIT_AMOUNT

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
                    f'Unable to create {blockchain.value} address for wallet {wallet.creator.address}',
                )

            WalletDepositAddress.objects.create(
                wallet=wallet,
                blockchain=blockchain,
                address=response['data']['address'],
            )


@db_periodic_task(crontab(minute='*/3'))
@lock_task('move-funds-to-master-wallet-lock')
def move_funds_to_master_wallet():
    for wallet in Wallet.objects.filter(balance__gte=MINIMUM_ALLOWED_DEPOSIT_AMOUNT):
        wallet_info_response = circle_api.get_wallet_info(wallet.provider_id)
        if wallet_info_response is None:
            continue

        usd_balance = next(filter(lambda x: x['currency'] == 'USD', wallet_info_response['data']['balances']), None)
        if usd_balance is None:
            continue

        amount = Decimal(usd_balance['amount'])
        move_to_master_wallet_response = circle_api.move_to_master_wallet(
            wallet_id=wallet.provider_id,
            amount=amount,
            master_wallet_id=settings.CIRCLE_MASTER_WALLET_ID,
        )
        if move_to_master_wallet_response is None:
            continue

        Transaction.objects.create(
            amount=amount,
            account=wallet.creator,
            status=TransactionStatus.PENDING,
            tx_type=TransactionType.MOVE_TO_MASTER_WALLET,
            metadata=move_to_master_wallet_response['data'],
            narration=f'Transfer {amount} USDC to master wallet',
        )


@db_periodic_task(crontab(minute='*/2'))
def periodically_check_for_wallets_without_deposit_addresses():
    wallet_without_addresses = Wallet.objects.annotate(deposit_addresses_count=Count('deposit_addresses')).filter(
        deposit_addresses_count__lt=len(Blockchain),
    )
    with transaction.atomic():
        for wallet in wallet_without_addresses:
            create_deposit_addresses_for_wallet.schedule((wallet.id,), delay=1)
