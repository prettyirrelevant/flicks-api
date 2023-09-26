from django.conf import settings

from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticated

from services.s3 import get_pre_signed_upload_url

from utils.responses import error_response, success_response

from .serializers import PreSignedURLSerializer


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
