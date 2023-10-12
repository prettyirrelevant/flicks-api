from typing import ClassVar

from django.db.models import Q

from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, RetrieveAPIView, get_object_or_404

from utils.responses import success_response

from .models import Creator
from .permissions import IsAuthenticated
from .serializers import (
    CreatorSerializer,
    MinimalCreatorSerializer,
    CreatorCreationSerializer,
    CreatorWithoutWalletSerializer,
)


class CreatorCreationAPIView(GenericAPIView):
    serializer_class = CreatorCreationSerializer
    permission_classes: ClassVar[list] = []

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        Creator.objects.create(**serializer.validated_data)
        return success_response('Creator created successfully.')


class CreatorAPIView(RetrieveAPIView):
    lookup_field = 'address'
    serializer_class = CreatorSerializer
    permission_classes = (IsAuthenticated,)
    queryset = Creator.objects.select_related('wallet').prefetch_related('wallet__deposit_addresses')

    def get_serializer_class(self):
        if self.request.user.address == self.get_object().address:
            return CreatorSerializer

        return CreatorWithoutWalletSerializer

    def retrieve(self, request, *args, **kwargs):  # noqa: PLR6301
        response = super().retrieve(request, *args, **kwargs)
        return success_response(data=response.data, status_code=response.status_code)

    def get_object(self):
        qs = self.get_queryset()
        obj = get_object_or_404(qs, address=self.request.user.address)
        self.check_object_permissions(self.request, obj)

        return obj


class SearchCreatorsAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = MinimalCreatorSerializer

    def get(self, request, *args, **kwargs):  # noqa: PLR6301 ARG002
        q = request.query_params.get('q')
        if q is None:
            raise serializers.ValidationError('`q` query parameter is required.')

        # This can be improved to use Postgres FTS but for now this should be sufficient.
        qs = Creator.objects.filter(Q(address__icontains=q) | Q(moniker__icontains=q))
        serializer = MinimalCreatorSerializer(qs, many=True)

        return success_response(serializer.data)
