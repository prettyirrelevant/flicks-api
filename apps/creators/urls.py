from django.urls import path

from .views import CreatorAPIView

urlpatterns = [
    path('creators/me', CreatorAPIView.as_view(), name='my-profile'),
]
