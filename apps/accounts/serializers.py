from rest_framework import serializers

from .models import Wallet, Account, WalletDepositAddress


class WalletDepositAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletDepositAddress
        fields = ('id', 'address', 'chain', 'created_at', 'updated_at')


class WalletSerializer(serializers.ModelSerializer):
    deposit_addresses = WalletDepositAddressSerializer(many=True)

    class Meta:
        model = Wallet
        fields = ('id', 'balance', 'deposit_addresses', 'created_at', 'updated_at')


class AccountSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer()

    class Meta:
        model = Account
        fields = (
            'id',
            'address',
            'email',
            'wallet',
            'moniker',
            'is_verified',
            'is_suspended',
            'suspension_reason',
            'created_at',
            'updated_at',
        )
