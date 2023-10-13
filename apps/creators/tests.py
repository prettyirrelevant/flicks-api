import logging
from unittest.mock import patch

from solders.keypair import Keypair

from django.test import TestCase

from rest_framework.test import APIClient

from apps.creators.models import Creator
from apps.subscriptions.choices import SubscriptionType

from utils.mock import MockResponse

WALLET_CREATION_RESPONSE = """
    {
        "data": {
            "walletId": "434000",
            "entityId": "fc988ed5-c129-4f70-a064-e5beb7eb8e32",
            "type": "end_user_wallet",
            "description": "Treasury Wallet",
            "balances": [
                {
                    "amount": "3.14",
                    "currency": "USD"
                }
            ]
        }
    }
"""


class AccountTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.keypair, self.creator = self.create_creator()  # pylint: disable=no-value-for-parameter

        logging.disable(logging.CRITICAL)

    def tearDown(self):  # noqa: PLR6301
        logging.disable(logging.NOTSET)

    @staticmethod
    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def create_creator(mock_post):  # noqa: ARG004
        keypair = Keypair()
        creator = Creator.objects.create(
            moniker='bonfida.sol',
            image_url='https://google.com',
            banner_url='https://google.com',
            address=str(keypair.pubkey()),
            subscription_type=SubscriptionType.FREE,
            is_verified=True,
        )

        return keypair, creator

    def test_get_profile_without_credentials(self):
        response = self.client.get(f'/creators/{self.keypair.pubkey()}')
        self.assertContains(response, 'Authentication credentials were not provided.', status_code=401)
        self.assertContains(response, 'NotAuthenticated', status_code=401)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_get_profile_with_valid_credentials(self, mock_post):  # noqa: ARG002
        signature = self.keypair.sign_message(b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path=f'/creators/{self.keypair.pubkey()}',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        response.json()['data'].pop('created_at')
        response.json()['data'].pop('updated_at')
        response.json()['data'].pop('id')
        response.json()['data'].pop('wallet')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            first={
                'bio': '',
                'social_links': {},
                'is_verified': True,
                'contents_count': 0,
                'is_suspended': False,
                'subscribers_count': 0,
                'subscription_info': {},
                'suspension_reason': '',
                'moniker': 'bonfida.sol',
                'subscription_type': 'free',
                'image_url': 'https://google.com',
                'banner_url': 'https://google.com',
                'address': str(self.keypair.pubkey()),
            },
            second=response.json()['data'],
        )

    def test_get_profile_with_invalid_credentials_signature_message(self):
        signature = self.keypair.sign_message(b'Message: Welcome to John Doe!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path='/creators/me',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        self.assertContains(response, 'Signature provided is not valid for the address.', status_code=401)
        self.assertContains(response, 'AuthenticationFailed', status_code=401)

    def test_get_profile_with_invalid_credentials_signature(self):
        signature = self.keypair.sign_message(b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path='/creators/me',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}rr'},
        )
        self.assertContains(response, 'string decoded to wrong size for signature', status_code=401)
        self.assertContains(response, 'AuthenticationFailed', status_code=401)

    def test_get_profile_with_invalid_credentials_addr(self):
        signature = self.keypair.sign_message(b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path='/creators/me',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}4f:{signature}'},
        )
        self.assertContains(response, 'String is the wrong size', status_code=401)
        self.assertContains(response, 'AuthenticationFailed', status_code=401)
