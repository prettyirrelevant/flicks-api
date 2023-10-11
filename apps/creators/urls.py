from django.urls import path

from .views import CreatorAPIView, CreatorCreationAPIView

urlpatterns = [
    path('me', CreatorAPIView.as_view(), name='my-profile'),
    path('', CreatorCreationAPIView.as_view(), name='create-creator'),
]
