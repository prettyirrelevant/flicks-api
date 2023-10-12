import logging

from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.mixins import ListModelMixin
from rest_framework.generics import GenericAPIView, get_object_or_404

from apps.creators.permissions import IsAuthenticated

from services.s3 import S3Service
from services.agora.token_builder import Role, RtcTokenBuilder

from utils.responses import success_response
from utils.pagination import CustomCursorPagination

from .models import Comment, Content, Livestream
from .permissions import IsCommentOwner, IsSubscribedToContent
from .serializers import (
    CommentSerializer,
    ContentSerializer,
    LiveStreamSerializer,
    CreateContentSerializer,
    UpdateContentSerializer,
    PreSignedURLListSerializer,
)

logger = logging.getLogger(__name__)


class PreSignedURLView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PreSignedURLListSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_data = {}
        for data in serializer.validated_data['files']:
            key = f"{data['file_type']}s/{self.request.user.address}/{data['file_name']}"
            s3_service = S3Service(
                bucket=settings.BUCKET_NAME,
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            response = s3_service.get_pre_signed_upload_url(
                key=key,
                file_type=data['file_type'],
                expiration=settings.PRESIGNED_URL_EXPIRATION,
            )
            response_data[data['file_name']] = response

        return success_response(response_data)


class ContentView(GenericAPIView, ListModelMixin):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateContentSerializer
        if self.request.method == 'PATCH':
            return UpdateContentSerializer
        return ContentSerializer

    def get_queryset(self):
        return Content.objects.filter(account=self.request.user).prefetch_related('media').order_by('-created_at')

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'content created successfully'}, 201)

    def patch(self, request, content_id):
        qs = self.get_queryset()
        content = get_object_or_404(qs, id=content_id)
        serializer = self.get_serializer(instance=content, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'content updated successfully'})

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)
        return success_response(response.data)


class LivestreamView(GenericAPIView, ListModelMixin):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination
    serializer_class = LiveStreamSerializer

    def get_queryset(self):
        return Livestream.objects.filter(account=self.request.user).order_by('-created_at')

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'livestream created successfully'}, 201)

    def patch(self, request, stream_id):
        stream = get_object_or_404(self.get_queryset(), id=stream_id)
        serializer = self.get_serializer(
            instance=stream,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'livestream updated successfully'})

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)
        return success_response(response.data)


class JoinLivestreamView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, stream_id):
        stream = get_object_or_404(Livestream.objects.all(), id=stream_id)
        role = Role.PUBLISHER if stream.account == self.request.user else Role.SUBSCRIBER
        token_builder = RtcTokenBuilder()
        token_expiration = (stream.start + stream.duration).timestamp()
        token = token_builder.build_token_with_user_account(
            settings.AGORA_APP_ID,
            settings.AGORA_APP_CERTIFICATE,
            str(stream.id),
            request.user.address,
            role,
            token_expiration,
            token_expiration,
        )
        return success_response({'token': token, 'channel_name': str(stream.id), 'user_account': request.user.address})


class LikesAPIView(APIView):
    queryset = Content.objects.get_queryset()
    permission_classes = (IsAuthenticated, IsSubscribedToContent)

    def get_object(self):
        obj = self.queryset.get(id=self.kwargs['content_id'])
        for permission in self.get_permissions():
            if not permission.has_object_permission(self.request, self, obj):
                self.permission_denied(
                    self.request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None),
                )

        return obj

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        content = self.get_object()
        content.likes.add(request.user)
        return success_response('Content liked successfully')

    def delete(self, request, *args, **kwargs):  # noqa: ARG002
        content = self.get_object()
        try:
            content.likes.remove(request.user)
        except Exception:
            logger.exception('An exception occurred while unliking content %s', content.id)

        return success_response('Content unliked successfully')


class CreateCommentAPIVIew(GenericAPIView):
    lookup_field = 'id'
    serializer_class = CommentSerializer
    queryset = Content.objects.get_queryset()
    permission_classes = (IsAuthenticated, IsSubscribedToContent)

    def get_object(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()

        obj = self.queryset.get(id=self.kwargs['content_id'])
        for permission in self.get_permissions():
            if not permission.has_object_permission(self.request, self, obj):
                self.permission_denied(
                    self.request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None),
                )

        return obj

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return success_response(data=serializer.data, status_code=status.HTTP_201_CREATED)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['content'] = self.get_object()
        return context


class DeleteCommentAPIView(GenericAPIView):
    queryset = Comment.objects.get_queryset()
    permission_classes = (IsAuthenticated, IsCommentOwner)

    def delete(self, request, *args, **kwargs):  # noqa: ARG002
        obj = self.get_object()
        obj.delete()

        return success_response(None, status_code=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        return Comment.objects.get(
            author=self.request.user,
            id=self.kwargs['comment_id'],
            content_id=self.kwargs['content_id'],
        )
