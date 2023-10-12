from django.urls import path

from .views import CreatorAPIView, SearchCreatorsAPIView, CreatorCreationAPIView

urlpatterns = [
    path('', CreatorCreationAPIView.as_view(), name='create-creator'),
    path('<str:address>', CreatorAPIView.as_view(), name='creator-detail'),
    path('search', SearchCreatorsAPIView.as_view(), name='search-creators'),
]
