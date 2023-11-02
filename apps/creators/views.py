from typing import ClassVar

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from django.db.models import Q
from django.conf import settings
from django.db import IntegrityError, transaction

from rest_framework.views import APIView
from rest_framework import status, serializers
from rest_framework.generics import ListAPIView, GenericAPIView, RetrieveAPIView, get_object_or_404

from apps.transactions.models import Transaction
from apps.contents.serializers import WithdrawalSerializer

from services.circle import CircleAPI

from utils.pagination import CustomCursorPagination
from utils.constants import PERCENTAGE_CUT_FROM_WITHDRAWALS
from utils.responses import error_response, success_response

from .models import Creator
from .choices import Blockchain
from .exceptions import BadGatewayError
from .permissions import IsAuthenticated
from .serializers import CreatorSerializer, MinimalCreatorSerializer, CreatorCreationSerializer


class CreatorCreationAPIView(GenericAPIView):
    serializer_class = CreatorCreationSerializer
    permission_classes: ClassVar[list] = []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            Creator.objects.create(**serializer.validated_data)
        except IntegrityError as e:
            return error_response(str(e), status_code=status.HTTP_409_CONFLICT, errors=[])

        return success_response('Creator created successfully.', status_code=status.HTTP_201_CREATED)


class CreatorAPIView(RetrieveAPIView):
    lookup_field = 'address'
    serializer_class = CreatorSerializer
    permission_classes: ClassVar[list] = []
    queryset = Creator.objects.select_related('wallet').prefetch_related(
        'wallet__deposit_addresses',
        'contents',
        'subscribers',
        'nft_subscriptions',
        'monetary_subscriptions',
    )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return success_response(data=response.data, status_code=response.status_code)

    def get_object(self):
        qs = self.get_queryset()
        obj = get_object_or_404(qs, address=self.kwargs['address'])
        self.check_object_permissions(self.request, obj)

        return obj


class SearchCreatorsAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = MinimalCreatorSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description='Query string to search for creator(s)',
                type=openapi.TYPE_STRING,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        q = request.query_params.get('q')
        if q is None:
            raise serializers.ValidationError('`q` query parameter is required.')

        # This can be improved to use Postgres FTS but for now this should be sufficient.
        qs = Creator.objects.filter(Q(address__icontains=q) | Q(moniker__icontains=q))
        serializer = MinimalCreatorSerializer(qs, many=True)

        return success_response(serializer.data)


class MonikerAvailabilityAPIView(APIView):
    permission_classes: ClassVar[list] = []

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description='Moniker to check for its availability',
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        q = request.query_params.get('q')
        if q is None:
            raise serializers.ValidationError('`q` query parameter is required.')

        qs = Creator.objects.filter(moniker=q.lower())
        if qs.exists():
            return error_response(message='Moniker is already taken.', errors=[], status_code=status.HTTP_409_CONFLICT)

        return success_response(data='Moniker is available to use.')


class CreatorWithdrawalAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = WithdrawalSerializer
    queryset = Creator.objects.get_queryset()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data['amount']
        with transaction.atomic():
            self.request.user.wallet.withdraw(amount)
            circle_api = CircleAPI(api_key=settings.CIRCLE_API_KEY, base_url=settings.CIRCLE_API_BASE_URL)

            withdrawal_response = circle_api.make_withdrawal(
                chain=Blockchain.SOLANA.value,
                amount=PERCENTAGE_CUT_FROM_WITHDRAWALS * amount,
                destination_address=self.request.user.address,
                master_wallet_id=settings.CIRCLE_MASTER_WALLET_ID,
            )
            if withdrawal_response is None:
                raise BadGatewayError('Unable to process your withdrawal at this time. Please try again later.')

            Transaction.create_withdrawal(
                creator=self.request.user,
                metadata=withdrawal_response['data'],
                amount=amount,
            )

        return success_response('Withdrawal is being processed.')


class SuggestedCreatorAPIView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = MinimalCreatorSerializer
    pagination_class = CustomCursorPagination

    def get_queryset(self):
        return Creator.objects.all().exclude(address=self.request.user.address)

    def get(self, request, *args, **kwargs):
        response = self.list(request, args, kwargs)
        return success_response(response.data)
