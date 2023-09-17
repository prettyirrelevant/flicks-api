from django.urls import path

from .views import ProfileAPIView

urlpatterns = [
    path('accounts/me', ProfileAPIView.as_view(), name='my-profile'),
]
