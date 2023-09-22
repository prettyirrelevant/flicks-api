import json
import contextlib

from django.db import IntegrityError

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from utils.responses import success_response

from .parsers import PlainTextParser
from .models import Webhook, WebhookType, WebhookStatus


class WebhookView(APIView):
    permission_classes = (AllowAny,)
    parser_classes = (PlainTextParser,)

    def post(self, request, *args, **kwargs):  # noqa: PLR6301 ARG002
        data = json.loads(request.data.decode('utf-8'), strict=False)
        if data['Type'] == 'SubscriptionConfirmation':
            with contextlib.suppress(IntegrityError):
                Webhook.objects.create(
                    payload=data,
                    message_id=data['MessageId'],
                    status=WebhookStatus.PENDING,
                    notification_type=WebhookType.SUBSCRIPTION_CONFIRMATION,
                )

        if data['Type'] == 'Notification':
            with contextlib.suppress(IntegrityError):
                Webhook.objects.create(
                    payload=data,
                    message_id=data['MessageId'],
                    status=WebhookStatus.PENDING,
                    notification_type=WebhookType.TRANSFERS,
                )

        return success_response(data=None)