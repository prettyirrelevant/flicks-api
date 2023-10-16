from datetime import timedelta

from solders.pubkey import Pubkey

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin

from apps.creators.models import Creator
from apps.transactions.models import Transaction
from apps.creators.permissions import IsAuthenticated

from services.sharingan import SharinganService

from utils.responses import success_response

from .choices import SubscriptionType, SubscriptionDetailStatus
from .models import NFTSubscription, FreeSubscription, SubscriptionDetail, MonetarySubscription
from .serializers import (
    NFTSubscriptionSerializer,
    FreeSubscriptionSerializer,
    DummySubscriptionSerializer,
    MonetarySubscriptionSerializer,
)


class SubscriptionsAPIView(GenericAPIView, CreateModelMixin):
    serializer_class = DummySubscriptionSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return super().get_serializer_class()

        subscription_type = self.request.data.pop('type')
        if subscription_type is None:
            raise ParseError('`type` is missing from request payload')

        if subscription_type == SubscriptionType.FREE:
            return FreeSubscriptionSerializer

        if subscription_type == SubscriptionType.MONETARY:
            return MonetarySubscriptionSerializer

        if subscription_type == SubscriptionType.NFT:
            return NFTSubscriptionSerializer

        raise ParseError(f'{subscription_type} is not a supported subscription type')

    def put(self, request, *args, **kwargs):
        """
        When **type=free**, only **status** is needed.
        When **type=monetary**, **status** and **amount** are needed.
        When **type=nft**, **status**, **collection_name**, **collection_address**, **collection_image_url** and **collection_description** are needed.
        """  # noqa: E501

        response = self.create(request, *args, *kwargs)
        return success_response(data=response.data, status_code=response.status_code)

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        nft_subscriptions = NFTSubscription.objects.filter(creator=self.request.user)
        nft_subscriptions_serializer = NFTSubscriptionSerializer(nft_subscriptions, many=True)

        free_subscriptions = FreeSubscription.objects.filter(creator=self.request.user)
        free_subscriptions_serializer = FreeSubscriptionSerializer(free_subscriptions, many=True)

        monetary_subscriptions = MonetarySubscription.objects.filter(creator=self.request.user)
        monetary_subscriptions_serializer = MonetarySubscriptionSerializer(monetary_subscriptions, many=True)

        return success_response(
            {
                'nft': nft_subscriptions_serializer.data,
                'free': free_subscriptions_serializer.data,
                'monetary': monetary_subscriptions_serializer.data,
            },
        )


class SubscribeToCreatorAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    sharingan_service = SharinganService(settings.SHARINGAN_BASE_URL)

    def validate_creator_address(self):
        creator_address = self.kwargs['address']
        public_key = Pubkey.from_string(creator_address)
        if not public_key.is_on_curve():
            raise serializers.ValidationError('Invalid address provided for creator')

        if self.request.user.address == creator_address:
            raise serializers.ValidationError('You cannot subscribe to yourself')

        try:
            creator = Creator.objects.get(address=creator_address)
        except Creator.DoesNotExist as e:
            raise serializers.ValidationError('Creator does not exist') from e

        return creator

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        creator = self.validate_creator_address()
        subscriber = request.user

        with transaction.atomic():
            if creator.subscription_type == SubscriptionType.FREE:
                self.handle_free_subscription(creator, subscriber)
            elif creator.subscription_type == SubscriptionType.NFT:
                self.handle_nft_subscription(creator, subscriber)
            elif creator.subscription_type == SubscriptionType.MONETARY:
                self.handle_monetary_subscription(creator, subscriber)
            else:
                raise serializers.ValidationError('Invalid subscription type')

            return success_response(data='Subscription created successfully')

    @staticmethod
    def handle_free_subscription(creator: 'Creator', subscriber: 'Creator'):
        subscription_info = SubscriptionDetail.objects.filter(
            creator=creator,
            subscriber=subscriber,
        ).first()

        # there's an active subscription to the creator
        if (
            subscription_info is not None
            and subscription_info.status == SubscriptionDetailStatus.ACTIVE
            and subscription_info.expires_at > timezone.now()
        ):
            return subscription_info

        # subscription has expired or was cancelled
        if subscription_info is not None and subscription_info.status != SubscriptionDetailStatus.ACTIVE:
            subscription_info.status = SubscriptionDetailStatus.ACTIVE
            subscription_info.expires_at += timedelta(weeks=520)  # ~10 years in weeks
            subscription_info.save()

        # no subscription to creator was found
        free_subscription = FreeSubscription.objects.get(creator=creator)
        return SubscriptionDetail.objects.create(
            creator=creator,
            subscriber=subscriber,
            subscription_object=free_subscription,
            status=SubscriptionDetailStatus.ACTIVE,
            expires_at=timezone.now() + timedelta(weeks=520),  # ~10 years in weeks
        )

    def handle_nft_subscription(self, creator: 'Creator', subscriber: 'Creator'):
        subscription_info = SubscriptionDetail.objects.filter(
            creator=creator,
            subscriber=subscriber,
        ).first()

        # there's an active subscription to the creator
        if (
            subscription_info is not None
            and subscription_info.status == SubscriptionDetailStatus.ACTIVE
            and subscription_info.expires_at > timezone.now()
        ):
            return subscription_info

        # subscription has expired or was cancelled
        nft_subscription = NFTSubscription.objects.get(creator=creator)
        if subscription_info is not None and subscription_info.status != SubscriptionDetailStatus.ACTIVE:
            response = self.sharingan_service.has_nft_in_collection(
                subscriber.address,
                nft_subscription.collection_name,
            )
            if response is None:
                raise serializers.ValidationError(
                    f'You do not own an NFT in {nft_subscription.collection_name}. '
                    f'Reach out to support if this is a mistake',
                )

            subscription_info.status = SubscriptionDetailStatus.ACTIVE
            subscription_info.expires_at += timedelta(days=1)
            subscription_info.save()

        # no subscription to creator was found
        response = self.sharingan_service.has_nft_in_collection(subscriber.address, nft_subscription.collection_name)
        if response is None:
            raise serializers.ValidationError(
                f'You do not own an NFT in {nft_subscription.collection_name}. '
                f'Reach out to support if this is a mistake',
            )

        return SubscriptionDetail.objects.create(
            creator=creator,
            subscriber=subscriber,
            subscription_object=nft_subscription,
            status=SubscriptionDetailStatus.ACTIVE,
            expires_at=timezone.now() + timedelta(days=1),
        )

    @staticmethod
    def handle_monetary_subscription(creator: 'Creator', subscriber: 'Creator'):
        subscription_info = SubscriptionDetail.objects.filter(
            creator=creator,
            subscriber=subscriber,
        ).first()

        # there's an active subscription to the creator
        if (
            subscription_info is not None
            and subscription_info.status == SubscriptionDetailStatus.ACTIVE
            and subscription_info.expires_at > timezone.now()
        ):
            return subscription_info

        # subscription has expired or was cancelled
        monetary_subscription = MonetarySubscription.objects.get(creator=creator)
        if subscription_info is not None and subscription_info.status != SubscriptionDetailStatus.ACTIVE:
            if subscriber.wallet.balance < monetary_subscription.amount:
                raise serializers.ValidationError(
                    'You do not have sufficient balance to subscribe to this creator. '
                    'Top up your balance and try again.',
                )

            subscriber.wallet.transfer(monetary_subscription.amount, creator.wallet)
            Transaction.create_subscription(monetary_subscription.amount, creator, subscriber)

            subscription_info.status = SubscriptionDetailStatus.ACTIVE
            subscription_info.expires_at += timedelta(days=30)
            subscription_info.save()

        # no subscription to creator was found
        if subscriber.wallet.balance < monetary_subscription.amount:
            raise serializers.ValidationError(
                'You do not have sufficient balance to subscribe to this creator. '
                'Top up your balance and try again.',
            )

        subscriber.wallet.transfer(monetary_subscription.amount, creator.wallet)
        Transaction.create_subscription(monetary_subscription.amount, creator, subscriber)

        return SubscriptionDetail.objects.create(
            creator=creator,
            subscriber=subscriber,
            status=SubscriptionDetailStatus.ACTIVE,
            subscription_object=monetary_subscription,
            expires_at=timezone.now() + timedelta(days=30),
        )
