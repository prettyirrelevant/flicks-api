from django.utils import timezone

from rest_framework.permissions import BasePermission

from apps.subscriptions.models import SubscriptionDetail
from apps.subscriptions.choices import SubscriptionDetailStatus


class IsSubscribedToContent(BasePermission):
    def has_object_permission(self, request, view, obj):  # noqa: PLR6301 ARG002
        subscription_detail_qs = SubscriptionDetail.objects.filter(
            creator=obj.account,
            subscriber=request.user,
            expires_at__lte=timezone.now(),
            status=SubscriptionDetailStatus.ACTIVE,
        )
        return subscription_detail_qs.exists()


class IsCommentOwner(BasePermission):
    def has_object_permission(self, request, view, obj):  # noqa: PLR6301 ARG002
        return obj.author == request.user
