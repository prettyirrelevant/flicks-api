import logging

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg.generators import OpenAPISchemaGenerator

from django.http import HttpRequest, JsonResponse

from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

from .responses import error_response

logger = logging.getLogger(__name__)


def custom_exception_handler(exception, context) -> Response | None:
    if not isinstance(exception, serializers.ValidationError):
        logger.exception(
            'An exception occurred while handling request %s',
            context['request'].get_full_path(),
            exc_info=exception,
        )

    response = exception_handler(exception, context)
    if response is None:
        return None

    if isinstance(exception, APIException):
        return error_response(
            message=exception.__class__.__name__,
            errors=[exception.detail] if isinstance(exception.detail, str) else exception.detail,
            status_code=response.status_code,
        )

    return error_response(message=str(exception), errors=None, status_code=response.status_code)


def handler_400(request, exception, *args, **kwargs):
    return JsonResponse(
        data={'message': 'Bad request', 'errors': None},
        status=status.HTTP_400_BAD_REQUEST,
    )


def handler_404(request, exception):
    return JsonResponse(data={'message': 'Not found', 'errors': None}, status=status.HTTP_404_NOT_FOUND)


def handler_500(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        data={
            'message': "We're sorry, but something went wrong on our end",
            'errors': None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@api_view()
def index_view(request):
    return Response(status=status.HTTP_200_OK)


class HttpAndHttpsOpenAPISchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):  # noqa: FBT002
        schema = super().get_schema(request, public)
        schema.schemes = ['http', 'https']
        return schema


docs_schema_view = get_schema_view(
    openapi.Info(
        title='Flicks API',
        default_version='v1',
        description='Flicks API',
        license=openapi.License(name='MIT License'),
    ),
    generator_class=HttpAndHttpsOpenAPISchemaGenerator,
    public=True,
    permission_classes=[AllowAny],
)
