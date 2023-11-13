import json
import uuid
import random
import string
import logging
import datetime
from decimal import Decimal
from unittest.mock import patch

from algosdk.account import generate_account
from rest_framework_simplejwt.tokens import RefreshToken

from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from apps.creators.models import Creator
from apps.subscriptions.choices import SubscriptionType
from apps.creators.tests import WALLET_CREATION_RESPONSE, WALLET_CREATION_RESPONSE_2
from apps.subscriptions.models import FreeSubscription, SubscriptionDetail, SubscriptionDetailStatus

from .models import Content, Livestream


class ContentsTest(TestCase):
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

        def tx_hash_generator():
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=52))  # noqa: S311

        return Creator.objects.create(
            address=address,
            moniker=moniker,
            is_verified=True,
            image_url='https://google.com',
            banner_url='https://google.com',
            subscription_type=SubscriptionType.FREE,
            spam_verification_tx=tx_hash_generator(),
        )

    def test_generate_presigned_url_without_credentials(self):
        response = self.client.post('/contents/get-upload-urls')
        self.assertContains(response, 'Authentication credentials were not provided.', status_code=401)
        self.assertContains(response, 'NotAuthenticated', status_code=401)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_generate_presigned_url_unsupported_file(self, mock_post):
        response = self.client.post(
            path='/contents/get-upload-urls',
            json={'files': [{'file_name': 'test.xlsx', 'file_type': 'xlsx'}]},
            headers=self.auth_header,
        )
        self.assertEqual(response.json()['message'], 'ValidationError')
        self.assertEqual(response.status_code, 400)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_generate_presigned_url_max_uploads_exceeded(self, mock_post):
        response = self.client.post(
            path='/contents/get-upload-urls',
            data=json.dumps(
                {
                    'files': [
                        {'file_name': 'test1.jpg', 'file_type': 'image'},
                        {'file_name': 'test2.jpg', 'file_type': 'image'},
                        {'file_name': 'test3.jpg', 'file_type': 'image'},
                        {'file_name': 'test4.jpg', 'file_type': 'image'},
                        {'file_name': 'test5.jpg', 'file_type': 'image'},
                        {'file_name': 'test6.jpg', 'file_type': 'image'},
                    ],
                },
            ),
            headers=self.auth_header,
            content_type='application/json',
        )
        self.assertEqual(response.json()['message'], 'ValidationError')
        self.assertEqual(
            response.json()['errors'],
            {'files': ['Max file upload per request exceeded']},
        )
        self.assertEqual(response.status_code, 400)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_generate_presigned_url_success(self, mock_post):
        data = {
            'files': [
                {'file_name': 'test.png', 'file_type': 'image'},
                {'file_name': 'test.mov', 'file_type': 'video'},
            ],
        }
        response = self.client.post(
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
            path='/contents/get-upload-urls',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data'].keys()), len(data['files']))

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_content_view(self, mock_post):
        # Create Content No Auth
        response = self.client.post(path='/contents/')
        self.assertEqual(response.status_code, 401)

        # Create Free Content
        data = {
            'caption': 'My First post',
            'content_type': 'free',
            'media': [
                {
                    'media_type': 'image',
                    's3_key': 'images/8LnFdWY5KjemEPqXVfco4h7RZubFds9iM7DPpinWZCnG/test.png',
                },
                {
                    'media_type': 'video',
                    's3_key': 'videos/vYBRhWTQPJXByU3ED3SpUWSqR3RnJ7eT1vJ6Ckfbuqq/test.mov',
                },
            ],
        }
        response = self.client.post(
            path='/contents/',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        content = Content.objects.get(creator__address=self.creator.address)
        self.assertEqual(content.caption, data['caption'])
        self.assertEqual(str(content.price), '0.00')
        self.assertEqual(content.content_type, 'free')
        self.assertEqual(content.media.all().count(), len(data['media']))

        # Create Paid Content With < $1.00
        data['price'] = '0.55'
        data['content_type'] = 'paid'
        response = self.client.post(
            path='/contents/',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            first=response.json()['errors']['non_field_errors'][0],
            second='Content with paywall must have a price of at least $1.00',
        )

        # Create Paid Content With $1.00
        data['price'] = '1'
        data['content_type'] = 'paid'
        response = self.client.post(
            path='/contents/',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)

        content = Content.objects.get(creator__address=self.creator.address, price__gte=Decimal('1'))
        self.assertEqual(content.caption, data['caption'])
        self.assertEqual(str(content.price), '1.00')
        self.assertEqual(content.content_type, 'paid')
        self.assertEqual(content.media.all().count(), len(data['media']))

        # Update Content Caption
        data = {'caption': 'New Caption'}
        response = self.client.patch(
            path=f'/contents/{content.id}',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )
        content.refresh_from_db()
        self.assertEqual(content.caption, data['caption'])
        self.assertEqual(response.status_code, 200)

        # Update Content Not Found
        response = self.client.patch(path=f'/contents/{uuid.uuid4()}', json=data, headers=self.auth_header)
        self.assertEqual(response.status_code, 404)

        # Fetch my Content View
        response = self.client.get(path=f'/contents/creators/{self.creator.address}', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['results']), 2)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE,
    )
    def test_livestream_view(self, mock_post):
        # Create Livestream With Future Start
        data = {
            'title': 'My First Livestream',
            'description': 'I just opened a Flicks Account. Join me for my first Livestream.',
            'start': (timezone.now() + datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'duration': datetime.timedelta(minutes=20).seconds,
        }
        response = self.client.post(
            data=json.dumps(data),
            headers=self.auth_header,
            path='/contents/livestreams',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        livestream = Livestream.objects.get(creator__address=self.creator.address)
        self.assertEqual(livestream.title, data['title'])
        self.assertEqual(livestream.description, data['description'])
        self.assertEqual(livestream.start.strftime('%Y-%m-%d %H:%M:%S'), data['start'])
        self.assertEqual(livestream.duration.seconds, data['duration'])

        # Create Instant Livestream
        instant_data = {
            'title': 'My Instant Livestream',
            'start': None,
            'description': 'I just opened a Flicks Account. Join me for my first Instant Livestream.',
            'duration': datetime.timedelta(minutes=15).seconds,
        }
        response = self.client.post(
            headers=self.auth_header,
            path='/contents/livestreams',
            data=json.dumps(instant_data),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        instant_livestream = Livestream.objects.get(
            creator__address=self.creator.address,
            title=instant_data['title'],
        )
        self.assertEqual(instant_livestream.title, instant_data['title'])
        self.assertEqual(instant_livestream.description, instant_data['description'])
        self.assertEqual(instant_livestream.duration.seconds, instant_data['duration'])

        # Create Livestream [Invalid Start]
        data['start'] = (timezone.now() - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        response = self.client.post(
            data=json.dumps(data),
            headers=self.auth_header,
            path='/contents/livestreams',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['start'][0], 'invalid start time')

        # Update Livestream
        data['start'] = (timezone.now() + datetime.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        data['title'] = 'Updated Livestream'
        data['description'] = 'Updated Description'
        data['duration'] = datetime.timedelta(minutes=15).seconds
        response = self.client.patch(
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
            path=f'/contents/livestreams/{livestream.id}',
        )
        livestream.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['id'], str(livestream.id))
        self.assertEqual(livestream.title, data['title'])
        self.assertEqual(livestream.description, data['description'])
        self.assertEqual(livestream.start.strftime('%Y-%m-%d %H:%M:%S'), data['start'])
        self.assertEqual(livestream.duration.seconds, data['duration'])

        # My Livestreams Test
        response = self.client.get(path='/contents/livestreams', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['results'][livestream.created_at.date().isoformat()]), 2)
        self.assertEqual(list(response.json()['results'].keys()), [livestream.created_at.date().isoformat()])

        # Join Livestream Test
        response = self.client.get(path=f'/contents/livestreams/{livestream.id}/join', headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['user_account'], str(self.creator.address))
        self.assertEqual(response.json()['data']['channel_name'], str(livestream.id))
        self.assertIn('token', response.json()['data'])

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE_2,
    )
    def test_user_timeline_view(self, mock_post):
        # Free Content
        data = {
            'caption': 'My First post',
            'content_type': 'free',
            'media': [
                {
                    'media_type': 'image',
                    's3_key': 'images/8LnFdWY5KjemEPqXVfco4h7RZubFds9iM7DPpinWZCnG/test.png',
                },
                {
                    'media_type': 'video',
                    's3_key': 'videos/vYBRhWTQPJXByU3ED3SpUWSqR3RnJ7eT1vJ6Ckfbuqq/test.mov',
                },
            ],
        }
        self.client.post(
            path='/contents/',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )
        # Paid Content
        data['price'] = '1'
        data['content_type'] = 'paid'
        data['caption'] = 'My First Paid Content'
        self.client.post(
            path='/contents/',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )

        # Create Subscriber
        _, address = generate_account()
        user = Creator.objects.create(
            moniker='nfdomains2.algo',
            image_url='https://google.com',
            banner_url='https://google.com',
            address=address,
            subscription_type=SubscriptionType.FREE,
            spam_verification_tx='DDDFFFF',
            is_verified=True,
        )
        free_subscription = FreeSubscription.objects.get(creator=self.creator)
        SubscriptionDetail.objects.create(
            creator=self.creator,
            subscriber=user,
            subscription_object=free_subscription,
            status=SubscriptionDetailStatus.ACTIVE,
            expires_at=timezone.now() + datetime.timedelta(days=1),
        )
        auth_header = {'Authorization': f'Bearer {RefreshToken.for_user(user).access_token}'}
        response = self.client.get(
            path='/contents/timeline',
            headers=auth_header,
            content_type='application/json',
        )
        contents = response.json()['results']
        for content in contents:
            if content['content_type'] == 'paid' and content['is_purchased'] is False:
                for media in content['media']:
                    self.assertEqual(media['url'], None)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE_2,
    )
    def test_media_view(self, mock_post):
        # Free Content
        data = {
            'caption': 'My First post',
            'content_type': 'free',
            'media': [
                {
                    'media_type': 'image',
                    's3_key': 'images/8LnFdWY5KjemEPqXVfco4h7RZubFds9iM7DPpinWZCnG/test.png',
                },
                {
                    'media_type': 'video',
                    's3_key': 'videos/vYBRhWTQPJXByU3ED3SpUWSqR3RnJ7eT1vJ6Ckfbuqq/test.mov',
                },
            ],
        }
        self.client.post(
            path='/contents/',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )
        # Paid Content
        data['price'] = '1'
        data['content_type'] = 'paid'
        data['caption'] = 'My First Paid Content'

        # Create User
        _, address = generate_account()
        user = Creator.objects.create(
            moniker='bonfida2.algo',
            image_url='https://google.com',
            banner_url='https://google.com',
            address=address,
            subscription_type=SubscriptionType.FREE,
            spam_verification_tx='XDDFFF',
            is_verified=True,
        )
        self.client.post(
            path='/contents/',
            data=json.dumps(data),
            headers=self.auth_header,
            content_type='application/json',
        )
        auth_header = {'Authorization': f'Bearer {RefreshToken.for_user(user).access_token}'}
        creator_media_response = self.client.get(
            path=f'/contents/media/{self.creator.address}',
            headers=auth_header,
            content_type='application/json',
        )
        self.assertEqual(creator_media_response.status_code, 200)
        self.assertEqual(len(creator_media_response.json()['data']['results']), 4)

    @patch(
        target='services.circle.CircleAPI._request',
        return_value=WALLET_CREATION_RESPONSE_2,
    )
    def test_discover_view(self, mock_post):
        creator_media_response = self.client.get(
            path='/contents/discover',
            headers=self.auth_header,
            content_type='application/json',
        )
        self.assertEqual(creator_media_response.status_code, 200)
