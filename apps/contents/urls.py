from django.urls import path

from .views import (
    MediaView,
    ContentView,
    DiscoverView,
    LikesAPIView,
    TimelineView,
    LivestreamView,
    PreSignedURLView,
    ContentListAPIView,
    JoinLivestreamView,
    CreateCommentAPIVIew,
    DeleteCommentAPIView,
    PayForContentAPIView,
)

urlpatterns = [
    path('', ContentView.as_view(), name='content'),
    path('creators/<str:address>', ContentListAPIView.as_view(), name='creators-content'),
    path('<uuid:content_id>/pay', PayForContentAPIView.as_view(), name='pay-for-content'),
    path('<uuid:content_id>/comments', CreateCommentAPIVIew.as_view(), name='create-comment'),
    path(
        '<uuid:content_id>/comments/<uuid:comment_id>',
        DeleteCommentAPIView.as_view(),
        name='delete-comment',
    ),
    path('livestreams', LivestreamView.as_view(), name='livestream-view'),
    path('discover', DiscoverView.as_view(), name='discover-view'),
    path('media/<str:address>', MediaView.as_view(), name='media-view'),
    path('timeline', TimelineView.as_view(), name='timeline-view'),
    path('livestreams/<uuid:stream_id>', LivestreamView.as_view(), name='update-livestream-view'),
    path('livestreams/<uuid:stream_id>/join', JoinLivestreamView.as_view(), name='join-livestream'),
    path('get-upload-urls', PreSignedURLView.as_view(), name='presigned-urls'),
    path('<uuid:content_id>', ContentView.as_view(), name='content detail'),
    path('<uuid:content_id>/likes', LikesAPIView.as_view(), name='content-like-dislike'),
]
