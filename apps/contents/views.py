from django.conf import settings

from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404

from apps.accounts.permissions import IsAuthenticated

from services.s3 import get_pre_signed_upload_url

from utils.pagination import CustomCursorPagination
from utils.responses import error_response, success_response

from .models import Content
from .serializers import ContentSerializer, PreSignedURLSerializer, CreateContentSerializer, UpdateContentSerializer


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

    def get_query_set(self):
        return Content.objects.filter(account=self.request.user).prefetch_related('media').order_by('-created_at')

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = CreateContentSerializer(data=self.request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'content created successfully'}, 201)

    def patch(self, request, content_id):
        qs = self.get_query_set()
        content = get_object_or_404(qs, id=content_id)
        serializer = UpdateContentSerializer(instance=content, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response({'message': 'content updated successfully'})

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        qs = self.get_query_set()
        page = self.paginator.paginate_queryset(qs, request, view=self)
        response = self.paginator.get_paginated_response(ContentSerializer(page, many=True).data)
        return success_response(response.data)
