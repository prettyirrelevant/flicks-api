from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.permissions import BasePermission

from .models import Account


class IsAuthenticated(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:  # noqa: ARG002, PLR6301
        return bool(request.user and isinstance(request.user, Account))
