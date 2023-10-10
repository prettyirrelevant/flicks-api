from typing import TYPE_CHECKING, Any, Union

from rest_framework import serializers

from .choices import SubscriptionType, SubscriptionStatus, SubscriptionDetailStatus
from .models import NFTSubscription, FreeSubscription, SubscriptionDetail, MonetarySubscription

if TYPE_CHECKING:
    from apps.creators.models import Creator


class BaseSubscriptionSerializer(serializers.ModelSerializer):
    @staticmethod
    def handle_free_subscription(
        creator: 'Creator',
        current_subscription: Union[FreeSubscription, MonetarySubscription, NFTSubscription],
    ) -> None:
        ...

    def get_current_subscription(
        self,
        subscription_type: SubscriptionType,
    ) -> Union[FreeSubscription, NFTSubscription, MonetarySubscription]:
        creator = self.context['request'].user

        if subscription_type == SubscriptionType.FREE:
            return FreeSubscription.objects.get(creator=creator)
        if subscription_type == SubscriptionType.NFT:
            return NFTSubscription.objects.get(creator=creator)
        if subscription_type == SubscriptionType.MONETARY:
            return MonetarySubscription.objects.get(creator=creator)

        raise AssertionError(f'Unsupported subscription type {subscription_type}.')

    @staticmethod
    def get_subscription_type_from_model(
        model: Union[type[FreeSubscription], type[MonetarySubscription], type[NFTSubscription]],
    ):
        if isinstance(model, FreeSubscription):
            return SubscriptionType.FREE
        if isinstance(model, MonetarySubscription):
            return SubscriptionType.MONETARY
        if isinstance(model, NFTSubscription):
            return SubscriptionType.NFT

        raise AssertionError(f'Unsupported subscription model {model.__name__}.')

    def create_subscription(
        self,
        subscription_model: Union[type[FreeSubscription], type[MonetarySubscription], type[NFTSubscription]],
        validated_data: dict[str, Any],
    ):
        creator = self.context['request'].user
        current_subscription = self.get_current_subscription(creator.subscription_type)

        if (
            isinstance(current_subscription, subscription_model)
            and validated_data['status'] == SubscriptionStatus.INACTIVE
        ):
            raise serializers.ValidationError(
                'You cannot deactivate this subscription as it is your active subscription.',
            )

        if validated_data['status'] == SubscriptionStatus.ACTIVE:
            if isinstance(current_subscription, FreeSubscription):
                self.handle_free_subscription(creator, current_subscription)

            creator.subscription_type = self.get_subscription_type_from_model(subscription_model)
            current_subscription.status = SubscriptionStatus.INACTIVE

            creator.save(update_fields=['subscription_type'])
            current_subscription.save(update_fields=['status'])

        return subscription_model.objects.get_or_create(
            creator=creator,
            defaults=validated_data,
        )


class FreeSubscriptionSerializer(BaseSubscriptionSerializer, serializers.ModelSerializer):
    class Meta:
        model = FreeSubscription
        fields = ('id', 'status', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self, validated_data):
        return self.create_subscription(FreeSubscription, validated_data)


class MonetarySubscriptionSerializer(BaseSubscriptionSerializer):
    class Meta:
        model = MonetarySubscription
        fields = ('id', 'amount', 'status', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    @staticmethod
    def handle_free_subscription(
        creator: 'Creator',
        current_subscription: Union[FreeSubscription, MonetarySubscription, NFTSubscription],
    ) -> None:
        SubscriptionDetail.objects.filter(
            creator=creator,
            subscription_id=current_subscription.id,
        ).update(
            status=SubscriptionDetailStatus.CANCELLED,
        )

    def create(self, validated_data):
        return self.create_subscription(MonetarySubscription, validated_data)


class NFTSubscriptionSerializer(BaseSubscriptionSerializer):
    class Meta:
        model = NFTSubscription
        fields = (
            'id',
            'collection_name',
            'collection_image_url',
            'collection_description',
            'collection_address',
            'status',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    @staticmethod
    def handle_free_subscription(
        creator: 'Creator',
        current_subscription: Union[FreeSubscription, MonetarySubscription, NFTSubscription],
    ) -> None:
        SubscriptionDetail.objects.filter(
            creator=creator,
            subscription_id=current_subscription.id,
        ).update(
            status=SubscriptionDetailStatus.CANCELLED,
        )

    def create(self, validated_data):
        return self.create_subscription(NFTSubscription, validated_data)
