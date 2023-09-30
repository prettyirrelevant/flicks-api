from django.conf import settings

from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from apps.accounts.permissions import IsAuthenticated

from services.s3 import get_pre_signed_upload_url
from services.agora.token_builder import Role, RtcTokenBuilder

from utils.pagination import CustomCursorPagination
from utils.responses import error_response, success_response

from .models import Content, Livestream
from .serializers import (
    ContentSerializer,
    LiveStreamSerializer,
    PreSignedURLSerializer,
    CreateContentSerializer,
    UpdateContentSerializer,
)


class PreSignedURLView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = PreSignedURLSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        if len(validated_data) > settings.MAX_FILE_UPLOAD_PER_REQUEST:
            return error_response('max file upload per request exceeded', {})
        response_data = {}
        for data in validated_data:
            key = f"{data['file_type']}s/{self.request.user.address}/{data['file_name']}"
            response = get_pre_signed_upload_url(
                settings.BUCKET_NAME,
                key,
                data['file_type'],
                settings.PRESIGNED_URL_EXPIRATION,
            )
            response_data[data['file_name']] = response
        return success_response(response_data)


class ContentView(APIView):
    permission_classes = (IsAuthenticated,)
    paginator = CustomCursorPagination()

    def get_queryset(self):
        return Content.objects.filter(account=self.request.user).prefetch_related('media').order_by('-created_at')

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = CreateContentSerializer(data=self.request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'content created successfully'}, 201)

    def patch(self, request, content_id):
        qs = self.get_queryset()
        content = get_object_or_404(qs, id=content_id)
        serializer = UpdateContentSerializer(instance=content, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'content updated successfully'})

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        qs = self.get_queryset()
        page = self.paginator.paginate_queryset(qs, request, view=self)
        response = self.paginator.get_paginated_response(ContentSerializer(page, many=True).data)
        return success_response(response.data)


class LivestreamView(APIView):
    permission_classes = (IsAuthenticated,)
    paginator = CustomCursorPagination()

    def get_queryset(self):
        return Livestream.objects.filter(account=self.request.user).order_by('-created_at')

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = LiveStreamSerializer(data=self.request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'livestream created successfully'}, 201)

    def patch(self, request, stream_id):
        stream = get_object_or_404(self.get_queryset(), id=stream_id)
        serializer = LiveStreamSerializer(
            instance=stream,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'livestream updated successfully'})

    def get(self, request):
        qs = self.get_queryset()
        page = self.paginator.paginate_queryset(qs, request, view=self)
        response = self.paginator.get_paginated_response(LiveStreamSerializer(page, many=True).data)
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
