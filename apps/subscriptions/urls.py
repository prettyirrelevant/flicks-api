from django.urls import path

from .views import SubscriptionsAPIView, SubscribeToCreatorAPIView

urlpatterns = [
    path('', SubscriptionsAPIView.as_view(), name='subscriptions'),
    path(
        'creators/<address>/subscribe',
        SubscribeToCreatorAPIView.as_view(),
        name='subscribe-to-creator',
    ),
]
