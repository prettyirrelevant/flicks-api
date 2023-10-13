# Create your views here.
from rest_framework.generics import ListAPIView

from apps.creators.permissions import IsAuthenticated

from utils.pagination import CustomCursorPagination

from .serializers import TransactionSerializer
from .models import Transaction, TransactionType


class TransactionView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomCursorPagination
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return (
            Transaction.objects.filter(account=self.request.user)
            .exclude(tx_type=TransactionType.MOVE_TO_MASTER_WALLET)
            .order_by('-created_at')
        )
