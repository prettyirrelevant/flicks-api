from rest_framework import serializers

from .models import Account


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('address', 'email', 'moniker', 'is_verified', 'is_suspended', 'suspension_reason')
