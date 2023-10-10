from rest_framework.exceptions import ParseError
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin

from apps.creators.permissions import IsAuthenticated

from utils.responses import success_response

from .choices import SubscriptionType
from .models import NFTSubscription, FreeSubscription, MonetarySubscription
from .serializers import NFTSubscriptionSerializer, FreeSubscriptionSerializer, MonetarySubscriptionSerializer


class SubscriptionsAPIView(GenericAPIView, CreateModelMixin):
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        subscription_type = self.request.data.get('type')
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
        request.data.pop('type')

        response = self.create(request, *args, *kwargs)
        return success_response(data=response.data, status_code=response.status_code)

    def get(self, request, *args, **kwargs):
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


class SubscribeToCreatorAPIView(GenericAPIView):
    ...
