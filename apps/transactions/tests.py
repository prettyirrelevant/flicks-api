import logging
from unittest.mock import patch

from algosdk.account import generate_account
from rest_framework_simplejwt.tokens import RefreshToken

from django.test import TestCase

from rest_framework.test import APIClient

from apps.creators.models import Creator
from apps.subscriptions.choices import SubscriptionType
from apps.creators.tests import WALLET_CREATION_RESPONSE


class TransactionsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.creator = self.create_creator('nfdomains.algo')  # pylint: disable=no-value-for-parameter
        self.auth_header = {'Authorization': f'Bearer {RefreshToken.for_user(self.creator).access_token}'}

        logging.disable(logging.CRITICAL)

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

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_transactions_view(self, mock_post):
        response = self.client.get(path='/transactions/', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'data': {'next': None, 'previous': None, 'results': []}})
