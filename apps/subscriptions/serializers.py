from rest_framework import serializers

from .models import NFTSubscription, FreeSubscription, MonetarySubscription


class FreeSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FreeSubscription
        fields = ('id', 'status', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self):
        ...


class MonetarySubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonetarySubscription
        fields = ('id', 'amount', 'status', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def create(self):
        ...


class NFTSubscriptionSerializer(serializers.ModelSerializer):
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

    def create(self):
        ...
