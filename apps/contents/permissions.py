from django.utils import timezone

from rest_framework.permissions import BasePermission

from apps.subscriptions.models import SubscriptionDetail
from apps.subscriptions.choices import SubscriptionDetailStatus

from .choices import ContentType


class IsSubscribedToCreator(BasePermission):
    def has_object_permission(self, request, view, obj):  # noqa: PLR6301 ARG002
        if request.user == obj.creator:
            return True

        subscription_detail_qs = SubscriptionDetail.objects.filter(
            creator=obj.creator,
            subscriber=request.user,
            expires_at__lte=timezone.now(),
            status=SubscriptionDetailStatus.ACTIVE,
        )
        return subscription_detail_qs.exists()


class IsSubscribedToContent(BasePermission):
    def has_object_permission(self, request, view, obj):  # noqa: PLR6301 ARG002
        if obj.content_type == ContentType.FREE:
            return True

        return obj.purchases.filter(id=request.user.id).exists()


class IsCommentOwner(BasePermission):
    def has_object_permission(self, request, view, obj):  # noqa: PLR6301 ARG002
        return obj.author == request.user
