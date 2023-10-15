import json
import logging
from decimal import Decimal

import requests
from huey import crontab
from huey.contrib.djhuey import lock_task, db_periodic_task

from django.db import transaction

from apps.creators.models import Wallet
from apps.creators.choices import Blockchain
from apps.transactions.models import Transaction
from apps.transactions.choices import TransactionType, TransactionStatus

from utils.constants import MINIMUM_ALLOWED_DEPOSIT_AMOUNT

from .models import Webhook, WebhookType, WebhookStatus

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute='*/2'))
@lock_task('handle-pending-webhooks-lock')
def handle_pending_webhooks():
    for webhook in Webhook.objects.filter(status=WebhookStatus.PENDING):
        if webhook.notification_type == WebhookType.SUBSCRIPTION_CONFIRMATION:
            handle_subscription_confirmation_webhook(webhook)

        elif webhook.notification_type == WebhookType.TRANSFERS:
            message = json.loads(webhook.payload['Message'], strict=False)
            if (
                message['transfer']['source']['type'] == 'blockchain'
                and message['transfer']['destination']['type'] == 'wallet'
            ):
                try:
                    handle_wallet_deposits_webhook(message['transfer'], webhook)
                except Exception:
                    logger.exception('Encountered an error while resolving a deposit webhook')
                    continue

            elif (
                message['transfer']['source']['type'] == 'wallet'
                and message['transfer']['destination']['type'] == 'wallet'
            ):
                try:
                    handle_transfer_to_master_wallet_webhook(message['transfer'], webhook)
                except Exception:
                    logger.exception('Encountered an error while resolving a transfer to master wallet webhook')
                    continue

            elif (
                message['transfer']['source']['type'] == 'wallet'
                and message['transfer']['destination']['type'] == 'blockchain'
            ):
                try:
                    handle_withdrawal_webhook(message['transfer'], webhook)
                except Exception:
                    logger.exception('Encountered an error while resolving a withdrawal to a creator address')
                    continue


@transaction.atomic()
def handle_wallet_deposits_webhook(message, webhook):
    amount = Decimal(message['amount']['amount'])
    network = Blockchain(message['source']['chain']).name.title()
    if (
        amount < MINIMUM_ALLOWED_DEPOSIT_AMOUNT
        or message['amount']['currency'] != 'USD'
        or message['status'] != 'complete'
    ):
        webhook.status = WebhookStatus.COMPLETED
        webhook.save()
        return

    wallet = Wallet.objects.get(provider_id=message['destination']['id'])
    Transaction.objects.create(
        amount=amount,
        metadata=message,
        account=wallet.creator,
        tx_type=TransactionType.CREDIT,
        status=TransactionStatus.SUCCESSFUL,
        narration=f'{amount} USDC top up via {network}',
    )
    wallet.top_up(amount)
    webhook.status = WebhookStatus.COMPLETED
    webhook.save()


@transaction.atomic()
def handle_transfer_to_master_wallet_webhook(message, webhook):
    if message['status'] not in {'complete', 'failed'}:
        webhook.status = WebhookStatus.COMPLETED
        webhook.save()
        return

    txn = Transaction.objects.get(metadata__id=message['id'])
    if txn.status in {TransactionStatus.SUCCESSFUL, TransactionStatus.FAILED}:
        webhook.status = WebhookStatus.COMPLETED
        webhook.save()
        return

    txn.metadata = message
    txn.status = TransactionStatus.SUCCESSFUL if message['status'] == 'complete' else TransactionStatus.FAILED
    txn.save()

    webhook.status = WebhookStatus.COMPLETED
    webhook.save()


def handle_subscription_confirmation_webhook(webhook):
    url = webhook.payload['SubscribeURL']
    try:
        response = requests.get(url=url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.exception('Circle notification confirmation error @ url %s with response %s', url, e.response.json())
    except Exception:
        logger.exception('Circle notification confirmation error @ url %s', url)
    else:
        webhook.status = WebhookStatus.COMPLETED
        webhook.save()


@transaction.atomic()
def handle_withdrawal_webhook(message, webhook):
    if message['status'] not in {'complete', 'failed'}:
        webhook.status = WebhookStatus.COMPLETED
        webhook.save()
        return

    transactions = Transaction.objects.filter(metadata__id=message['id'])
    if transactions.first().status in {TransactionStatus.SUCCESSFUL, TransactionStatus.FAILED}:
        webhook.status = WebhookStatus.COMPLETED
        webhook.save()
        return

    transactions.update(
        metadata=message,
        status=TransactionStatus.SUCCESSFUL if message['status'] == 'complete' else TransactionStatus.FAILED,
    )
    webhook.status = WebhookStatus.COMPLETED
    webhook.save()
