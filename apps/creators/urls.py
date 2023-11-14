from rest_framework_simplejwt.views import TokenRefreshView

from django.urls import path

from .views import (
    CreatorAPIView,
    SearchCreatorsAPIView,
    CreatorCreationAPIView,
    NonceGenerationAPIView,
    SuggestedCreatorAPIView,
    CreatorWithdrawalAPIView,
    MonikerAvailabilityAPIView,
    CreatorAuthenticationAPIView,
)

urlpatterns = [
    path('', CreatorCreationAPIView.as_view(), name='create-creator'),
    path('auth/refresh', TokenRefreshView.as_view(), name='refresh-token'),
    path('auth/nonces', NonceGenerationAPIView.as_view(), name='generate-nonce'),
    path('auth', CreatorAuthenticationAPIView.as_view(), name='authenticate-creator'),
    path('search', SearchCreatorsAPIView.as_view(), name='search-creators'),
    path('suggestions', SuggestedCreatorAPIView.as_view(), name='suggested-creators'),
    path(
        'withdrawals',
        CreatorWithdrawalAPIView.as_view(),
        name='withdraw-money-from-creator-wallet',
    ),
    path(
        'moniker-availability',
        MonikerAvailabilityAPIView.as_view(),
        name='moniker-availability',
    ),
    path('<str:address>', CreatorAPIView.as_view(), name='creator-detail'),
]
