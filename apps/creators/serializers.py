from solders.pubkey import Pubkey

from django.conf import settings

from rest_framework import serializers

from apps.subscriptions.choices import SubscriptionType

from services.sharingan import SharinganService

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
    contents_count = serializers.SerializerMethodField()
    subscribers_count = serializers.SerializerMethodField()
    subscription_info = serializers.SerializerMethodField()

    def get_contents_count(self, obj):  # noqa: PLR6301
        return obj.contents.count()

    def get_subscribers_count(self, obj):  # noqa: PLR6301
        return obj.subscribers.count()

    def get_subscription_info(self, obj):  # noqa: PLR6301
        if obj.subscription_type == SubscriptionType.NFT:
            subscription = obj.nft_subscriptions.first()
            return {
                'collection_name': subscription.collection_name,
                'collection_image': subscription.collection_image_url,
                'collection_address': subscription.collection_address,
                'collection_description': subscription.collection_description,
            }
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
    image_url = serializers.URLField(required=True)
    banner_url = serializers.URLField(required=True)
    bio = serializers.CharField(max_length=200, required=False)
    address = serializers.CharField(max_length=44, required=True)
    moniker = serializers.CharField(max_length=5000, required=True)

    def validate_address(self, value):  # noqa: PLR6301
        public_key = Pubkey.from_string(value)
        if not public_key.is_on_curve():
            raise serializers.ValidationError('Invalid address provided.')

        return value

    def validate(self, attrs):  # noqa: PLR6301
        sharingan_service = SharinganService(settings.SHARINGAN_BASE_URL)
        response = sharingan_service.resolve_address_to_sns(attrs['address'])
        if response is None and attrs['moniker'].endswith('.sol'):
            raise serializers.ValidationError('You cannot use an SNS as a moniker if you do not own it.')

        if (
            response is not None
            and attrs['moniker'].endswith('.sol')
            and f'{response["domainName"]}.sol' != attrs['moniker']
        ):
            raise serializers.ValidationError('Moniker type of SNS selected does not belong to address.')

        social_links = {}
        is_verified = False
        if response is not None:
            response.pop('domainName')
            if 'twitter' in response:
                is_verified = True

            social_links = response

        attrs['is_verified'] = is_verified
        attrs['social_links'] = social_links
        attrs['subscription_type'] = SubscriptionType.FREE
        return attrs
