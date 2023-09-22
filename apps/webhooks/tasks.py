import json
import logging
from decimal import Decimal

import requests
from huey import crontab
from huey.contrib.djhuey import lock_task, db_periodic_task

from django.db import transaction

from utils.constants import MINIMUM_ALLOWED_DEPOSIT_AMOUNT

from apps.accounts.models import Wallet
from apps.accounts.choices import Blockchain
from apps.transactions.models import Transaction
from apps.transactions.choices import TransactionType, TransactionStatus

from .models import Webhook, WebhookType, WebhookStatus

logger = logging.getLogger(__name__)


@db_periodic_task(crontab(minute='*/2'))
@lock_task('handle-pending-webhooks-lock')
def handle_pending_webhooks():
    for webhook in Webhook.objects.filter(status=WebhookStatus.PENDING):
        if webhook.notification_type == WebhookType.SUBSCRIPTION_CONFIRMATION:
            is_success = handle_subscription_confirmation_webhook(webhook.payload)
            if is_success:
                webhook.status = WebhookStatus.COMPLETED
                webhook.save()
        elif webhook.notification_type == WebhookType.TRANSFERS:
            message = json.loads(webhook.payload['Message'], strict=False)
            if (
                message['transfer']['source']['type'] == 'blockchain'
                and message['transfer']['destination']['type'] == 'wallet'
            ):
                try:
                    with transaction.atomic():
                        is_success = handle_wallet_deposits_webhook(message)
                        if is_success:
                            webhook.status = WebhookStatus.COMPLETED
                            webhook.save()
                except Exception:
                    logger.exception('Encountered an error while resolving a deposit webhook, skipping...')
                    continue


def handle_wallet_deposits_webhook(data):
    amount = Decimal(data['transfer']['amount']['amount'])
    network = Blockchain(data['transfer']['source']['chain']).name.title()
    if amount < MINIMUM_ALLOWED_DEPOSIT_AMOUNT:
        return True

    if data['transfer']['amount']['currency'] != 'USD':
        return True

    wallet = Wallet.objects.get(provider_id=data['transfer']['destination']['id'])
    Transaction.objects.create(
        amount=amount,
        metadata=data,
        account=wallet.account,
        tx_type=TransactionType.CREDIT,
        status=TransactionStatus.SUCCESSFUL,
        narration=f'{amount} USDC top up via {network} network',
    )
    wallet.top_up(amount)
    return True


def handle_subscription_confirmation_webhook(data):
    url = data['SubscribeURL']
    try:
        response = requests.get(url=url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.exception('Circle notification confirmation error @ url %s with response %s', url, e.response.json())
        return False
    except Exception:
        logger.exception('Circle notification confirmation error @ url %s', url)
        return False

    return True
