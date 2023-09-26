from django.urls import path

from .views import PreSignedURLView

urlpatterns = [
    path('contents/get-upload-urls', PreSignedURLView.as_view(), name='presigned-urls'),
]
