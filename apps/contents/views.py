import logging
import itertools
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, GenericAPIView, get_object_or_404
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, DestroyModelMixin, RetrieveModelMixin

from apps.transactions.models import Transaction
from apps.creators.permissions import IsAuthenticated
from apps.subscriptions.models import SubscriptionDetail
from apps.subscriptions.choices import SubscriptionDetailStatus

from services.s3 import S3Service
from services.agora.token_builder import Role, RtcTokenBuilder

from utils.constants import ZERO
from utils.pagination import CustomCursorPagination
from utils.responses import error_response, success_response

from .choices import ContentType
from .models import Media, Comment, Content, Livestream
from .permissions import (
    IsCommentOwner,
    IsContentOwner,
    IsLivestreamOwner,
    IsSubscribedToContent,
    IsSubscribedToCreator,
)
from .serializers import (
    MediaSerializer,
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


class ContentView(GenericAPIView):
    queryset = Content.objects.get_queryset()
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination

    def get_permissions(self):
        permissions = super().get_permissions()
        if self.request.method in {'DELETE', 'PATCH'}:
            return [*permissions, IsContentOwner()]

        return permissions

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateContentSerializer

        if self.request.method == 'PATCH':
            return UpdateContentSerializer

        return super().get_serializer_class()

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(creator=self.request.user).order_by('-created_at')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response('content created successfully', 201)

    def patch(self, request, content_id):
        qs = self.get_queryset()
        content = get_object_or_404(qs, id=content_id)
        serializer = self.get_serializer(instance=content, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response('content updated successfully')

    def delete(self, request, content_id):
        content = get_object_or_404(self.get_queryset(), id=content_id)
        if content.price != ZERO and content.purchases.exists():
            return error_response(
                errors=[],
                message='cannot delete a content that has already been purchased by at least one subscriber',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        content.delete()
        return success_response('content delete successfully', status_code=status.HTTP_204_NO_CONTENT)


class ContentListAPIView(ListAPIView):
    serializer_class = ContentSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Content.objects.get_queryset()
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()

        address = self.kwargs['address']
        return qs.filter(creator__address=address)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        return success_response(response.data, response.status_code)


class PayForContentAPIView(APIView):
    permission_classes = (IsAuthenticated, IsSubscribedToCreator)
    queryset = Content.objects.filter(content_type=ContentType.PAID)

    def post(self, request, *args, **kwargs):
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
    serializer_class = LiveStreamSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        return Livestream.objects.filter(creator=self.request.user).order_by('-created_at')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, 201)

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            data = self.group_livestreams(page)
            return self.get_paginated_response(data)

        data = self.group_livestreams(page)
        return success_response(data)

    def group_livestreams(self, results):
        grouped_data = defaultdict(list)
        for key, group in itertools.groupby(results, lambda x: x.created_at.date()):
            for entry in group:
                grouped_data[key.isoformat()].append(self.get_serializer(instance=entry).data)

        return grouped_data


class FetchUpdateDeleteLivestreamView(GenericAPIView, DestroyModelMixin, UpdateModelMixin, RetrieveModelMixin):
    lookup_field = 'id'
    serializer_class = LiveStreamSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Livestream.objects.get_queryset()

    def get_permissions(self):
        if self.request.method in {'PATCH', 'DELETE'}:
            return IsAuthenticated(), IsLivestreamOwner()

        return super().get_permissions()

    def patch(self, request, *args, **kwargs):
        response = self.partial_update(request, *args, **kwargs)
        return success_response(response.data, status_code=response.status_code)

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)
        return success_response(response.data, status_code=response.status_code)

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)
        return success_response(response.data, status_code=response.status_code)


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

        token_builder = RtcTokenBuilder()
        role = Role.PUBLISHER if stream.creator == self.request.user else Role.SUBSCRIBER
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
        return success_response(
            {
                'token': token,
                'channel_name': str(stream.id),
                'user_account': request.user.address,
            }
        )


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

    def post(self, request, *args, **kwargs):
        content = self.get_object()
        content.likes.add(request.user)
        return success_response('Content liked successfully')

    def delete(self, request, *args, **kwargs):
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return success_response(data='Comment created successfully.', status_code=status.HTTP_201_CREATED)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['content'] = self.get_object()
        return context


class DeleteCommentAPIView(APIView):
    queryset = Comment.objects.get_queryset()
    permission_classes = (IsAuthenticated, IsCommentOwner)

    def delete(self, request, *args, **kwargs):
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


class TimelineView(ListAPIView):
    serializer_class = ContentSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        return Content.objects.filter(
            creator__in=self.request.user.subscriptions.filter(status=SubscriptionDetailStatus.ACTIVE).values(
                'creator',
            ),
        ).order_by('-created_at')


class MediaView(ListAPIView):
    serializer_class = MediaSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        creator = self.kwargs['address']
        qs = Media.objects.filter(content__creator__address=creator)
        return qs.order_by('-created_at')

    def get(self, request, *args, **kwargs):
        response = self.list(request, args, kwargs)
        return success_response(response.data)


class DiscoverView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ContentSerializer
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        return (
            Content.objects.filter(content_type=ContentType.FREE)
            .exclude(creator__address=self.request.user.address)
            .order_by('-created_at')
        )

    def get(self, request, *args, **kwargs):
        response = self.list(request, args, kwargs)
        return success_response(response.data)
