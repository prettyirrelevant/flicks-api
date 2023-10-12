import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.mixins import ListModelMixin
from rest_framework.generics import GenericAPIView, get_object_or_404

from apps.transactions.models import Transaction
from apps.creators.permissions import IsAuthenticated
from apps.subscriptions.models import SubscriptionDetail
from apps.subscriptions.choices import SubscriptionDetailStatus

from services.s3 import S3Service
from services.agora.token_builder import Role, RtcTokenBuilder

from utils.pagination import CustomCursorPagination
from utils.responses import error_response, success_response

from .choices import ContentType
from .models import Comment, Content, Livestream
from .permissions import IsCommentOwner, IsSubscribedToContent, IsSubscribedToCreator
from .serializers import (
    ContentSerializer,
    LiveStreamSerializer,
    CreateCommentSerializer,
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
        return Content.objects.filter(creator=self.request.user).prefetch_related('media').order_by('-created_at')

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


class PayForContentAPIView(APIView):
    permission_classes = (IsAuthenticated, IsSubscribedToCreator)
    queryset = Content.objects.filter(content_type=ContentType.PAID)

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        content = self.get_object()
        payer = request.user
        if payer.wallet.balance < content.price:
            return error_response(
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST,
                message='Insufficient balance to purchase this content.',
            )

        with transaction.atomic():
            payer.wallet.transfer(amount=content.price, recipient=content.creator)
            Transaction.create_payment_for_content(amount=content.price, creator=content.creator, subscriber=payer)

            content.purchases.add(payer)

        return success_response('Content paid for successfully')

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


class LivestreamView(GenericAPIView, ListModelMixin):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination
    serializer_class = LiveStreamSerializer

    def get_queryset(self):
        return Livestream.objects.filter(creator=self.request.user).order_by('-created_at')

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'livestream created successfully'}, 201)

    def patch(self, request, stream_id):
        stream = get_object_or_404(self.get_queryset(), id=stream_id)
        serializer = self.get_serializer(
            partial=True,
            instance=stream,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'livestream updated successfully'})

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)
        return success_response(response.data)


class JoinLivestreamView(APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def is_subscribed(creator, subscriber):
        if creator == subscriber:
            return True

        subscription_detail_qs = SubscriptionDetail.objects.filter(
            creator=creator,
            subscriber=subscriber,
            expires_at__lte=timezone.now(),
            status=SubscriptionDetailStatus.ACTIVE,
        )
        return subscription_detail_qs.exists()

    def get(self, request, stream_id):
        stream = get_object_or_404(Livestream.objects.all(), id=stream_id)
        if not self.is_subscribed(creator=stream.creator, subscriber=self.request.user):
            return error_response(
                errors=None,
                status_code=status.HTTP_403_FORBIDDEN,
                message='You are not subscribed to this creator',
            )

        role = Role.PUBLISHER if stream.creator == self.request.user else Role.SUBSCRIBER
        token_builder = RtcTokenBuilder()
        token_expiration = (stream.start + stream.duration).timestamp()
        token = token_builder.build_token_with_user_account(
            role=role,
            channel_name=str(stream.id),
            account=request.user.address,
            app_id=settings.AGORA_APP_ID,
            token_expire=token_expiration,
            privilege_expire=token_expiration,
            app_certificate=settings.AGORA_APP_CERTIFICATE,
        )
        return success_response({'token': token, 'channel_name': str(stream.id), 'user_account': request.user.address})


class LikesAPIView(APIView):
    queryset = Content.objects.get_queryset()
    permission_classes = (IsAuthenticated, IsSubscribedToCreator, IsSubscribedToContent)

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
    queryset = Content.objects.get_queryset()
    serializer_class = CreateCommentSerializer
    permission_classes = (IsAuthenticated, IsSubscribedToCreator, IsSubscribedToContent)

    def get_object(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()

        obj = self.get_queryset().get(id=self.kwargs['content_id'])
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


class DeleteCommentAPIView(APIView):
    queryset = Comment.objects.get_queryset()
    permission_classes = (IsAuthenticated, IsCommentOwner)

    def delete(self, request, *args, **kwargs):  # noqa: ARG002
        obj = self.get_object()
        obj.delete()

        return success_response(None, status_code=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()

        obj = self.queryset.get(
            author=self.request.user,
            id=self.kwargs['comment_id'],
            content_id=self.kwargs['content_id'],
        )
        for permission in self.get_permissions():
            if not permission.has_object_permission(self.request, self, obj):
                self.permission_denied(
                    self.request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None),
                )

        return obj
