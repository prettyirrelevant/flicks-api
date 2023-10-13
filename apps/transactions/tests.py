import logging
from unittest.mock import patch

from solders.keypair import Keypair

from django.test import TestCase

from rest_framework.test import APIClient

from apps.creators.models import Creator
from apps.subscriptions.choices import SubscriptionType
from apps.creators.tests import WALLET_CREATION_RESPONSE


class TransactionsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.keypair, self.creator = self.create_creator('bonfida.sol')  # pylint: disable=no-value-for-parameter
        self.message = b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app'
        self.signature = self.keypair.sign_message(message=self.message)
        self.auth_header = {
            'Authorization': f'Signature {self.keypair.pubkey()}:{self.signature}',
        }

        logging.disable(logging.CRITICAL)

    @staticmethod
    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def create_creator(moniker: str, mock_post):  # noqa: ARG004
        keypair = Keypair()
        creator = Creator.objects.create(
            moniker=moniker,
            image_url='https://google.com',
            banner_url='https://google.com',
            address=str(keypair.pubkey()),
            subscription_type=SubscriptionType.FREE,
            is_verified=True,
        )

        return keypair, creator

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_transactions_view(self, mock_post):  # noqa: ARG002
        response = self.client.get(path='/transactions/', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
