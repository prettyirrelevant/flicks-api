from rest_framework.generics import RetrieveAPIView, get_object_or_404

from utils.responses import success_response

from .models import Account
from .serializers import ProfileSerializer


class ProfileAPIView(RetrieveAPIView):
    queryset = Account.objects.get_queryset()
    serializer_class = ProfileSerializer

    def retrieve(self, request, *args, **kwargs):  # noqa: PLR6301
        response = super().retrieve(request, *args, **kwargs)
        return success_response(data=response.data, status_code=response.status_code)

    def get_object(self):
        qs = self.get_queryset()
        obj = get_object_or_404(qs, address=self.request.user.address)
        self.check_object_permissions(self.request, obj)

        return obj
