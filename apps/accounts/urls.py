from django.urls import path

from .views import MyAccountAPIView

urlpatterns = [
    path('accounts/me', MyAccountAPIView.as_view(), name='my-profile'),
]
