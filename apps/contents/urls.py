from django.urls import path

from .views import ContentView, PreSignedURLView, LivestreamView

urlpatterns = [
    path('contents', ContentView.as_view(), name='content'),
    path('contents/<uuid:content_id>', ContentView.as_view(), name='content detail'),
    path('contents/get-upload-urls', PreSignedURLView.as_view(), name='presigned-urls'),
    path('contents/livestream', LivestreamView.as_view(), name='livestream-view'),
    path('contents/livestream/<uuid:stream_id>', LivestreamView.as_view(), name='update-livestream-view')
]
