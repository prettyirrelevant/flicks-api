import json
import uuid
import datetime
from unittest.mock import patch

from solders.keypair import Keypair

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from apps.accounts.tests import WALLET_CREATION_RESPONSE

from utils.mock import MockResponse

from .models import Content, Livestream


class ContentsTest(TestCase):
    def setUp(self):
        self.keypair = Keypair()
        self.client = APIClient()
        self.message = b'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app'
        self.signature = self.keypair.sign_message(message=self.message)
        self.auth_header = {
            'Authorization': f'Signature {self.keypair.pubkey()}:{self.signature}',
        }

    def test_generate_presigned_url_without_credentials(self):
        response = self.client.post('/api/contents/get-upload-urls')
        self.assertContains(response, 'Authentication credentials were not provided.', status_code=401)
        self.assertContains(response, 'NotAuthenticated', status_code=401)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_generate_presigned_url_unsupported_file(self, mock_post):  # noqa: ARG002
        response = self.client.post(
            path='/api/contents/get-upload-urls',
            data=json.dumps([{'file_name': 'test.xlsx', 'file_type': 'xlsx'}]),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.json()['message'], 'ValidationError')
        self.assertEqual(response.status_code, 400)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_generate_presigned_url_max_uploads_exceeded(self, mock_post):  # noqa: ARG002
        response = self.client.post(
            path='/api/contents/get-upload-urls',
            data=json.dumps(
                [
                    {'file_name': 'test1.jpg', 'file_type': 'image'},
                    {'file_name': 'test2.jpg', 'file_type': 'image'},
                    {'file_name': 'test3.jpg', 'file_type': 'image'},
                    {'file_name': 'test4.jpg', 'file_type': 'image'},
                    {'file_name': 'test5.jpg', 'file_type': 'image'},
                    {'file_name': 'test6.jpg', 'file_type': 'image'},
                ],
            ),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.json()['message'], 'max file upload per request exceeded')
        self.assertEqual(response.status_code, 400)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_generate_presigned_url_success(self, mock_post):  # noqa: ARG002
        # Presigned URL Generation
        files = [
            {'file_name': 'test.png', 'file_type': 'image'},
            {'file_name': 'test.mov', 'file_type': 'video'},
        ]
        response = self.client.post(
            path='/api/contents/get-upload-urls',
            data=json.dumps(files),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data'].keys()), len(files))

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_content_view(self, mock_post):  # noqa: ARG002
        # Create Content No Auth
        response = self.client.post(
            path='/api/contents',
        )
        self.assertEqual(response.status_code, 401)
        # Create Content
        data = {
            'caption': 'My First post',
            'media': [
                {'media_type': 'image', 's3_key': 'images/8LnFdWY5KjemEPqXVfco4h7RZubFds9iM7DPpinWZCnG/test.png'},
                {'media_type': 'video', 's3_key': 'videos/vYBRhWTQPJXByU3ED3SpUWSqR3RnJ7eT1vJ6Ckfbuqq/test.mov'},
            ],
        }
        response = self.client.post(
            path='/api/contents',
            data=json.dumps(data),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        content = Content.objects.get(account__address=self.keypair.pubkey())
        self.assertEqual(content.caption, data['caption'])
        self.assertEqual(content.media.all().count(), len(data['media']))
        # Update Content Caption
        data = {
            'caption': 'New Caption',
        }
        response = self.client.patch(
            path=f'/api/contents/{content.id}',
            data=json.dumps(data),
            content_type='application/json',
            headers=self.auth_header,
        )
        content.refresh_from_db()
        self.assertEqual(content.caption, data['caption'])
        self.assertEqual(response.status_code, 200)
        # Update Content Not Found
        response = self.client.patch(
            path=f'/api/contents/{uuid.uuid4()}',
            data=json.dumps(data),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 404)
        # Fetch my Content View
        response = self.client.get(
            path='/api/contents',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['results']), 1)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=MockResponse(text=WALLET_CREATION_RESPONSE, status_code=201),
    )
    def test_livestream_view(self, mock_post):  # noqa: ARG002
        # Create Livestream With Future Start
        data = {
            'title': 'My First Livestream',
            'description': 'I just opened a Flicks Account. Join me for my first Livestream.',
            'start': (timezone.now() + datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'duration': datetime.timedelta(minutes=20).seconds,
        }
        response = self.client.post(
            path='/api/contents/livestream',
            data=json.dumps(data),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        livestream = Livestream.objects.get(account__address=self.keypair.pubkey())
        self.assertEqual(livestream.title, data['title'])
        self.assertEqual(livestream.description, data['description'])
        self.assertEqual(livestream.start.strftime('%Y-%m-%d %H:%M:%S'), data['start'])
        self.assertEqual(livestream.duration.seconds, data['duration'])

        # Create Instant Livestream
        instant_data = {
            'title': 'My Instant Livestream',
            'start': None,
            'description': 'I just opened a Flicks Account. Join me for my first Instant Livestream.',
            'duration': datetime.timedelta(minutes=10).seconds,
        }
        response = self.client.post(
            '/api/contents/livestream',
            data=json.dumps(instant_data),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 201)
        instant_livestream = Livestream.objects.get(
            account__address=self.keypair.pubkey(),
            title=instant_data['title'],
        )
        self.assertEqual(instant_livestream.title, instant_data['title'])
        self.assertEqual(instant_livestream.description, instant_data['description'])
        self.assertEqual(instant_livestream.duration.seconds, instant_data['duration'])

        # Create Livestream [Invalid Start]
        data['start'] = (timezone.now() - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        response = self.client.post(
            path='/api/contents/livestream',
            data=json.dumps(data),
            content_type='application/json',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['start'][0], 'invalid start time')

        # Update Livestream
        data['start'] = (timezone.now() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        data['title'] = 'Updated Livestream'
        data['description'] = 'Updated Description'
        data['duration'] = datetime.timedelta(minutes=15).seconds
        response = self.client.patch(
            path=f'/api/contents/livestream/{livestream.id}',
            data=json.dumps(data),
            content_type='application/json',
            headers=self.auth_header,
        )
        livestream.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['message'], 'livestream updated successfully')
        self.assertEqual(livestream.title, data['title'])
        self.assertEqual(livestream.description, data['description'])
        self.assertEqual(livestream.start.strftime('%Y-%m-%d %H:%M:%S'), data['start'])
        self.assertEqual(livestream.duration.seconds, data['duration'])

        # My Livestreams Test
        response = self.client.get(
            path='/api/contents/livestream',
            headers=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['results']), 2)

        # Join Livestream Test
        response = self.client.get(path=f'/api/contents/livestream/{livestream.id}/join', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['user_account'], str(self.keypair.pubkey()))
        self.assertEqual(response.json()['data']['channel_name'], str(livestream.id))
        self.assertIn('token', response.json()['data'])
