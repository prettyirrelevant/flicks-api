from algosdk.constants import ADDRESS_LEN
from algosdk.encoding import is_valid_address

from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser

from rest_framework import serializers

from apps.subscriptions.models import SubscriptionDetail
from apps.subscriptions.choices import SubscriptionType, SubscriptionDetailStatus

from services.algorand import Algorand
from services.nf_domains import NFDomains

from .models import Wallet, Creator, WalletDepositAddress


class WalletDepositAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletDepositAddress
        fields = ('id', 'address', 'blockchain', 'created_at', 'updated_at')


class WalletSerializer(serializers.ModelSerializer):
    deposit_addresses = WalletDepositAddressSerializer(many=True)

    class Meta:
        model = Wallet
        fields = ('id', 'balance', 'deposit_addresses', 'created_at', 'updated_at')


class CreatorSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer()
    is_subscribed = serializers.SerializerMethodField()
    contents_count = serializers.SerializerMethodField()
    subscribers_count = serializers.SerializerMethodField()
    subscription_info = serializers.SerializerMethodField()

    def get_contents_count(self, obj):
        return obj.contents.count()

    def get_is_subscribed(self, obj):
        if isinstance(self.context['request'].user, AnonymousUser):
            return False

        status = SubscriptionDetail.objects.filter(
            creator=obj,
            status=SubscriptionDetailStatus.ACTIVE,
            subscriber=self.context['request'].user,
        )
        return status.exists()

    def get_subscribers_count(self, obj):
        return obj.subscribers.filter(status=SubscriptionDetailStatus.ACTIVE, expires_at__gte=timezone.now()).count()

    def get_subscription_info(self, obj):
        if obj.subscription_type == SubscriptionType.TOKEN_GATED:
            subscription = obj.token_gated_subscriptions.first()
            return {
                'token_id': subscription.token_id,
                'token_name': subscription.token_name,
                'token_decimals': subscription.token_decimals,
                'minimum_token_balance': subscription.minimum_token_balance,
            }
        # if obj.subscription_type == SubscriptionType.NFT:
        #     subscription = obj.nft_subscriptions.first()
        #     return {
        #         'collection_name': subscription.collection_name,
        #         'collection_image': subscription.collection_image_url,
        #         'collection_address': subscription.collection_address,
        #         'collection_description': subscription.collection_description,
        #     }
        if obj.subscription_type == SubscriptionType.MONETARY:
            subscription = obj.monetary_subscriptions.first()
            return {'amount': subscription.amount}

        return {}

    class Meta:
        model = Creator
        fields = (
            'id',
            'bio',
            'wallet',
            'address',
            'moniker',
            'image_url',
            'banner_url',
            'created_at',
            'updated_at',
            'is_verified',
            'social_links',
            'is_suspended',
            'is_subscribed',
            'contents_count',
            'subscription_info',
            'subscribers_count',
            'suspension_reason',
            'subscription_type',
        )


class MinimalCreatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Creator
        fields = (
            'id',
            'address',
            'moniker',
            'image_url',
            'is_verified',
            'subscription_type',
        )


class CreatorCreationSerializer(serializers.Serializer):
    image_url = serializers.URLField()
    banner_url = serializers.URLField()
    moniker = serializers.CharField(max_length=5000)
    address = serializers.CharField(max_length=ADDRESS_LEN)
    spam_verification_tx = serializers.CharField(max_length=200)
    bio = serializers.CharField(max_length=200, allow_blank=True, default='')

    def validate_address(self, value):
        if not is_valid_address(value):
            raise serializers.ValidationError('Invalid address provided.')

        return value

    def validate(self, attrs):
        algorand_service = Algorand(
            api_key=settings.PURESTAKE_API_KEY,
            algod_url=settings.PURESTAKE_ALGOD_URL,
            indexer_url=settings.PURESTAKE_INDEXER_URL,
        )
        tx_info = algorand_service.get_transaction(attrs['spam_verification_tx'])
        if tx_info is None:
            raise serializers.ValidationError('Invalid transaction ID provided.')

        if not (
            tx_info['tx-type'] == 'pay'
            and tx_info['sender'] == attrs['address']
            and 'payment-transaction' in tx_info
            and tx_info['payment-transaction']['receiver'] == settings.BURN_ADDRESS
            and tx_info['payment-transaction']['amount'] == 0
        ):
            raise serializers.ValidationError('Invalid transaction ID provided')

        nf_domains = NFDomains(settings.NFDOMAINS_BASE_URL)
        response = nf_domains.resolve_address(attrs['address'])
        if response is None and attrs['moniker'].endswith('.algo'):
            raise serializers.ValidationError('You cannot use an NFDomain name as a moniker if you do not own it.')

        if response is not None and attrs['moniker'].endswith('.algo') and response['domainName'] != attrs['moniker']:
            raise serializers.ValidationError('Moniker type of NFDomain name selected does not belong to address.')

        attrs['moniker'] = attrs['moniker'].lower()
        attrs['subscription_type'] = SubscriptionType.FREE
        attrs['is_verified'] = response is not None and 'twitter' in response['verified']
        attrs['social_links'] = {} if response is None else {**response['userDefined'], **response['verified']}

        attrs['social_links'].pop('caalgo', None)
        attrs['social_links'].pop('caAlgo', None)
        return attrs


class CreatorAuthenticationSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=ADDRESS_LEN)

    def validate_address(self, value):
        if not is_valid_address(value):
            raise serializers.ValidationError('Invalid algorand address provided.')

        return value
