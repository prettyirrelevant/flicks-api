from typing import ClassVar

from rest_framework.generics import GenericAPIView, RetrieveAPIView, get_object_or_404

from utils.responses import success_response

from .models import Creator
from .permissions import IsAuthenticated
from .serializers import CreatorSerializer, CreatorCreationSerializer


class CreatorCreationAPIView(GenericAPIView):
    serializer_class = CreatorCreationSerializer
    permission_classes: ClassVar[list] = []

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        Creator.objects.create(**serializer.validated_data)
        return success_response('Creator created successfully.')


class CreatorAPIView(RetrieveAPIView):
    queryset = Creator.objects.select_related('wallet').prefetch_related('wallet__deposit_addresses')
    permission_classes = (IsAuthenticated,)
    serializer_class = CreatorSerializer

    def retrieve(self, request, *args, **kwargs):  # noqa: PLR6301
        response = super().retrieve(request, *args, **kwargs)
        return success_response(data=response.data, status_code=response.status_code)

    def get_object(self):
        qs = self.get_queryset()
        obj = get_object_or_404(qs, address=self.request.user.address)
        self.check_object_permissions(self.request, obj)

        return obj
