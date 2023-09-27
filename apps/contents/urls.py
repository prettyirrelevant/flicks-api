from django.urls import path

from .views import PreSignedURLView, ContentView

urlpatterns = [
    path('contents', ContentView.as_view(), name='content'),
    path('contents/get-upload-urls', PreSignedURLView.as_view(), name='presigned-urls'),
]
