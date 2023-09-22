import json
import logging

from sns_message_validator import (
    SNSMessageValidator,
    InvalidCertURLException,
    InvalidMessageTypeException,
    InvalidSignatureVersionException,
    SignatureVerificationFailureException,
)

from django.http import HttpResponse

logger = logging.getLogger(__name__)


class CircleAPINotificationMiddleware:  # pylint: disable=too-few-public-methods
    def __init__(self, get_response):
        self.get_response = get_response
        self.sns_message_validator = SNSMessageValidator()

    def __call__(self, request):  # noqa: PLR0911
        if not (request.method == 'POST' and request.path == '/api/webhooks'):
            return self.get_response(request)

        try:
            self.sns_message_validator.validate_message_type(request.headers.get('x-amz-sns-message-type'))
        except InvalidMessageTypeException:
            logger.exception('Unable to validate Circle webhook due to invalid message type')
            return HttpResponse(status=400)

        try:
            message = json.loads(request.body.decode('utf-8'), strict=False)
        except json.decoder.JSONDecodeError:
            logger.exception('Unable to validate Circle webhook due to request body is not in json format')
            return HttpResponse(status=400)

        try:
            self.sns_message_validator.validate_message(message=message)
        except InvalidCertURLException:
            logger.exception('Unable to validate Circle webhook due to invalid certificate URL')
            return HttpResponse(status=400)
        except InvalidSignatureVersionException:
            logger.exception('Unable to validate Circle webhook due to invalid signature version')
            return HttpResponse(status=400)
        except SignatureVerificationFailureException:
            logger.exception('Unable to validate Circle webhook due to signature verification failure')
            return HttpResponse(status=400)

        return self.get_response(request)
