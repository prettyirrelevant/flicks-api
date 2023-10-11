from django.urls import path

from .views import CreatorAPIView, CreatorCreationAPIView

urlpatterns = [
    path('creators/me', CreatorAPIView.as_view(), name='my-profile'),
    path('creators', CreatorCreationAPIView.as_view(), name='create-creator'),
]
