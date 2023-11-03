from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.permissions import BasePermission

from .models import Creator


class IsAuthenticated(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(request.user and isinstance(request.user, Creator))
