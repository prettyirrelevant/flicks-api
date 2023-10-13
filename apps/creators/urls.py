from django.urls import path

from .views import CreatorAPIView, SearchCreatorsAPIView, CreatorCreationAPIView, MonikerAvailabilityAPIView

urlpatterns = [
    path('', CreatorCreationAPIView.as_view(), name='create-creator'),
    path('search', SearchCreatorsAPIView.as_view(), name='search-creators'),
    path('moniker-availability', MonikerAvailabilityAPIView.as_view(), name='moniker-availability'),
    path('<str:address>', CreatorAPIView.as_view(), name='creator-detail'),
]
