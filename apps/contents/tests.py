import json
from unittest.mock import patch

from solders.keypair import Keypair

from django.test import TestCase

from rest_framework.test import APIClient

from apps.accounts.tests import WALLET_CREATION_RESPONSE
from .models import Content

from utils.mock import MockResponse


class ContentsTest(TestCase):
    def setUp(self):
        self.keypair = Keypair()
        self.client = APIClient()
        self.message = b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app'

    def test_generate_presigned_url_without_credentials(self):
        response = self.client.post('/api/contents/get-upload-urls')
        self.assertContains(response, 'Authentication credentials were not provided.', status_code=401)
        self.assertContains(response, 'NotAuthenticated', status_code=401)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_generate_presigned_url_unsupported_file(self, mock_post):  # noqa: ARG002
        signature = self.keypair.sign_message(message=self.message)
        response = self.client.post(
            path='/api/contents/get-upload-urls',
            data=json.dumps([{'file_name': 'test.xlsx', 'file_type': 'xlsx'}]),
            content_type='application/json',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        self.assertEqual(response.json()['message'], 'ValidationError')
        self.assertEqual(response.status_code, 400)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_generate_presigned_url_max_uploads_exceeded(self, mock_post):  # noqa: ARG002
        signature = self.keypair.sign_message(self.message)
        response = self.client.post(
            path='/api/contents/get-upload-urls',
            data=json.dumps([
                {'file_name': 'test1.jpg', 'file_type': 'image'},
                {'file_name': 'test2.jpg', 'file_type': 'image'},
                {'file_name': 'test3.jpg', 'file_type': 'image'},
                {'file_name': 'test4.jpg', 'file_type': 'image'},
                {'file_name': 'test5.jpg', 'file_type': 'image'},
                {'file_name': 'test6.jpg', 'file_type': 'image'},
            ]),
            content_type='application/json',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        self.assertEqual(response.json()['message'], 'max file upload per request exceeded')
        self.assertEqual(response.status_code, 400)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_generate_presigned_url_success(self, mock_post):  # noqa: ARG002
        # Presigned URL Generation
        signature = self.keypair.sign_message(self.message)
        files = [
            {'file_name': 'test.png', 'file_type': 'image'},
            {'file_name': 'test.mov', 'file_type': 'video'},
        ]
        response = self.client.post(
            path='/api/contents/get-upload-urls',
            data=json.dumps(files),
            content_type='application/json',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data'].keys()), len(files))

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_create_content(self, mock_post):
        # Create Content No Auth
        response = self.client.post(
            path='/api/contents'
        )
        self.assertEqual(response.status_code, 401)
        # Create Content
        signature = self.keypair.sign_message(self.message)
        data = {
            "caption": "My First post",
            "media": [
                {"media_type": "image", "s3_key": "images/8LnFdWY5KjemEPqXVfco4h7RZubFds9iM7DPpinWZCnG/test.png"},
                {"media_type": "video", "s3_key": "videos/vYBRhWTQPJXByU3ED3SpUWSqR3RnJ7eT1vJ6Ckfbuqq/test.mov"}
            ]
        }
        response = self.client.post(
            path='/api/contents',
            data=json.dumps(data),
            content_type='application/json',
            headers={'Authorization': f'Signature {self.keypair.pubkey()}:{signature}'},
        )
        self.assertEqual(response.status_code, 201)
        content = Content.objects.get(account__address=self.keypair.pubkey())
        self.assertEqual(content.caption, data['caption'])
        self.assertEqual(content.media.all().count(), len(data['media']))
