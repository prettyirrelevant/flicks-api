from django.urls import path

from .views import (
    MediaView,
    ContentView,
    DiscoverView,
    LikesAPIView,
    LivestreamView,
    PreSignedURLView,
    ContentListAPIView,
    JoinLivestreamView,
    ContentTimelineView,
    CreateCommentAPIVIew,
    DeleteCommentAPIView,
    PayForContentAPIView,
    LiveStreamTimelineView,
    FetchUpdateDeleteLivestreamView,
)

urlpatterns = [
    path('', ContentView.as_view(), name='content'),
    path('discover', DiscoverView.as_view(), name='discover-view'),
    path('get-upload-urls', PreSignedURLView.as_view(), name='presigned-urls'),
    path('livestreams', LivestreamView.as_view(), name='livestream-view'),
    path('livestreams/timeline', LiveStreamTimelineView.as_view(), name='livestream-timeline-view'),
    path(
        'livestreams/<uuid:stream_id>/join',
        JoinLivestreamView.as_view(),
        name='join-livestream',
    ),
    path(
        'livestreams/<uuid:id>',
        FetchUpdateDeleteLivestreamView.as_view(),
        name='fetch-update-delete-livestream-view',
    ),
    path('timeline', ContentTimelineView.as_view(), name='content-timeline-view'),
    path('media/<str:address>', MediaView.as_view(), name='media-view'),
    path('creators/<str:address>', ContentListAPIView.as_view(), name='creators-content'),
    path('<uuid:content_id>/pay', PayForContentAPIView.as_view(), name='pay-for-content'),
    path(
        '<uuid:content_id>/comments',
        CreateCommentAPIVIew.as_view(),
        name='create-comment',
    ),
    path(
        '<uuid:content_id>/comments/<uuid:comment_id>',
        DeleteCommentAPIView.as_view(),
        name='delete-comment',
    ),
    path('<uuid:content_id>', ContentView.as_view(), name='content detail'),
    path('<uuid:content_id>/likes', LikesAPIView.as_view(), name='content-like-dislike'),
]
