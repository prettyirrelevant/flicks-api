from django.urls import path

from .views import (
    ContentView,
    LikesAPIView,
    LivestreamView,
    PreSignedURLView,
    JoinLivestreamView,
    CreateCommentAPIVIew,
)

urlpatterns = [
    path('', ContentView.as_view(), name='content'),
    path('<uuid:content_id>/comments', CreateCommentAPIVIew.as_view(), name='create-comment'),
    path(
        '<uuid:content_id>/comments/<uuid:comment_id>',
        CreateCommentAPIVIew.as_view(),
        name='delete-comment',
    ),
    path('livestreams', LivestreamView.as_view(), name='livestream-view'),
    path('livestreams/<uuid:stream_id>', LivestreamView.as_view(), name='update-livestream-view'),
    path('livestreams/<uuid:stream_id>/join', JoinLivestreamView.as_view(), name='join-livestream'),
    path('get-upload-urls', PreSignedURLView.as_view(), name='presigned-urls'),
    path('<uuid:content_id>', ContentView.as_view(), name='content detail'),
    path('<uuid:content_id>/likes', LikesAPIView.as_view(), name='content-like-dislike'),
]
