import json
import base64
import random
import string
import logging
from unittest.mock import patch

from algosdk.account import generate_account
from rest_framework_simplejwt.tokens import RefreshToken

from django.test import TestCase

from rest_framework.test import APIClient

from apps.creators.models import Creator
from apps.subscriptions.choices import SubscriptionType

WALLET_CREATION_RESPONSE = json.loads(
    """
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
""",
    strict=False,
)

WALLET_CREATION_RESPONSE_2 = json.loads(
    """
    {
        "data": {
            "walletId": "434001",
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
""",
    strict=False,
)


class AccountTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.creator = self.create_creator('nfdomains.algo')  # pylint: disable=no-value-for-parameter
        self.auth_header = {'Authorization': f'Bearer {RefreshToken.for_user(self.creator).access_token}'}

        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @staticmethod
    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def create_creator(moniker: str, mock_post):  # noqa: ARG004
        _, address = generate_account()
        return Creator.objects.create(
            address=address,
            moniker=moniker,
            is_verified=True,
            image_url='https://google.com',
            banner_url='https://google.com',
            subscription_type=SubscriptionType.FREE,
            spam_verification_tx='VA37N6HU3QBSR7KL4BZIIM464NXRH3FWY7LH7PHLF6W5NHOCPXA',
        )

    def test_get_profile_without_credentials(self):
        response = self.client.get(f'/creators/{self.creator.address}')
        self.assertEqual(response.status_code, 200)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_get_profile_with_valid_credentials(self, mock_post):
        response = self.client.get(
            path=f'/creators/{self.creator.address}',
            headers=self.auth_header,
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
                'is_subscribed': False,
                'subscribers_count': 0,
                'subscription_info': {},
                'suspension_reason': '',
                'moniker': 'nfdomains.algo',
                'subscription_type': 'free',
                'image_url': 'https://google.com',
                'banner_url': 'https://google.com',
                'address': self.creator.address,
            },
            second=response.json()['data'],
        )

    def test_get_profile_with_invalid_credentials_signature_message(self):
        def generate_random_jwt():
            return '.'.join(
                [
                    base64.urlsafe_b64encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode()).decode().rstrip('='),
                    base64.urlsafe_b64encode(
                        json.dumps(
                            {'data': ''.join(random.choices(string.ascii_letters + string.digits, k=10))}  # noqa: S311
                        ).encode()
                    )
                    .decode()
                    .rstrip('='),
                    ''.join(random.choices(string.ascii_letters + string.digits, k=43)),  # noqa: S311
                ]
            )

        response = self.client.get(
            path='/creators/me',
            headers={'Authorization': f'Bearer {generate_random_jwt()}'},
        )
        self.assertContains(
            response,
            'Given token not valid for any token type',
            status_code=401,
        )

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_get_suggested_creators(self, mock_post):
        response = self.client.get(path='/creators/suggestions', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
