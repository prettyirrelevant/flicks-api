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
    path('contents', ContentView.as_view(), name='content'),
    path('contents/<uuid:id>/comments', CreateCommentAPIVIew.as_view(), name='create-comment'),
    path(
        'contents/<uuid:content_id>/comments/<uuid:comment_id>',
        CreateCommentAPIVIew.as_view(),
        name='delete-comment',
    ),
    path('contents/livestream', LivestreamView.as_view(), name='livestream-view'),
    path('contents/livestream/<uuid:stream_id>', LivestreamView.as_view(), name='update-livestream-view'),
    path('contents/livestream/<uuid:stream_id>/join', JoinLivestreamView.as_view(), name='join-livestream'),
    path('contents/get-upload-urls', PreSignedURLView.as_view(), name='presigned-urls'),
    path('contents/<uuid:content_id>', ContentView.as_view(), name='content detail'),
    path('contents/<uuid:id>/likes', LikesAPIView.as_view(), name='content-like-dislike'),
]
