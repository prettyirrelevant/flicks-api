import logging

from solders.keypair import Keypair

from django.test import TestCase

from rest_framework.test import APIClient


class AccountTest(TestCase):
    def setUp(self):
        self.keypair = Keypair()
        self.client = APIClient()

        logging.disable(logging.CRITICAL)

    def tearDown(self):  # noqa: PLR6301
        logging.disable(logging.NOTSET)

    def test_get_profile_without_credentials(self):
        response = self.client.get('/api/accounts/me')
        self.assertContains(response, 'Authentication credentials were not provided.', status_code=401)
        self.assertContains(response, 'NotAuthenticated', status_code=401)

    def test_get_profile_with_valid_credentials(self):
        signature = self.keypair.sign_message(b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path='/api/accounts/me',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            first={
                'address': str(self.keypair.pubkey()),
                'email': '',
                'moniker': '',
                'is_verified': False,
                'is_suspended': False,
                'suspension_reason': '',
            },
            second=response.json()['data'],
        )

    def test_get_profile_with_invalid_credentials_signature_message(self):
        signature = self.keypair.sign_message(b'Message: Welcome to John Doe!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path='/api/accounts/me',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        self.assertContains(response, 'Signature provided is not valid for the address.', status_code=401)
        self.assertContains(response, 'AuthenticationFailed', status_code=401)

    def test_get_profile_with_invalid_credentials_signature(self):
        signature = self.keypair.sign_message(b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path='/api/accounts/me',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}rr'},
        )
        self.assertContains(response, 'string decoded to wrong size for signature', status_code=401)
        self.assertContains(response, 'AuthenticationFailed', status_code=401)

    def test_get_profile_with_invalid_credentials_addr(self):
        signature = self.keypair.sign_message(b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app')
        response = self.client.get(
            path='/api/accounts/me',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}4f:{signature}'},
        )
        self.assertContains(response, 'String is the wrong size', status_code=401)
        self.assertContains(response, 'AuthenticationFailed', status_code=401)
