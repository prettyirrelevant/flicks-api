from django.urls import path

from .views import (
    CreatorAPIView,
    SearchCreatorsAPIView,
    CreatorCreationAPIView,
    SuggestedCreatorAPIView,
    CreatorWithdrawalAPIView,
    MonikerAvailabilityAPIView,
)

urlpatterns = [
    path('', CreatorCreationAPIView.as_view(), name='create-creator'),
    path('suggestions', SuggestedCreatorAPIView.as_view(), name='suggested-creators'),
    path('<str:address>', CreatorAPIView.as_view(), name='creator-detail'),
    path('search', SearchCreatorsAPIView.as_view(), name='search-creators'),
    path('withdrawals', CreatorWithdrawalAPIView.as_view(), name='withdraw-money-from-creator-wallet'),
    path('moniker-availability', MonikerAvailabilityAPIView.as_view(), name='moniker-availability'),
]
