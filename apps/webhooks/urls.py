from django.urls import path

from .views import WebhookView

urlpatterns = [path('webhooks', WebhookView.as_view(), name='webhooks')]
