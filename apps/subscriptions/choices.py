from django.db import models


class SubscriptionType(models.TextChoices):
    NFT = 'nft'
    FREE = 'free'
    MONETARY = 'monetary'


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class SubscriptionDetailStatus(models.TextChoices):
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
