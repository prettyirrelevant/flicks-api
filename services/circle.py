import uuid
from typing import Any
from decimal import Decimal

from . import RequestMixin


class CircleAPI(RequestMixin):
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def ping(self) -> bool:
        response = self._request('GET', 'ping')
        return response.get('message') == 'pong'

    def make_withdrawal(
        self,
        amount: Decimal,
        master_wallet_id: int,
        destination_address: str,
        chain: str,
    ) -> dict[str, Any]:
        return self._request(
            method='POST',
            endpoint='v1/transfers',
            data={
                'idempotencyKey': str(uuid.uuid4()),
                'source': {
                    'type': 'wallet',
                    'id': str(master_wallet_id),
                },
                'destination': {
                    'type': 'blockchain',
                    'address': destination_address,
                    'chain': chain,
                },
                'amount': {'amount': f'{amount:.2f}', 'currency': 'USD'},
            },
        )

    def move_to_master_wallet(
        self,
        amount: Decimal,
        master_wallet_id: int,
        wallet_id: str,
    ) -> dict[str, Any]:
        return self._request(
            method='POST',
            endpoint='v1/transfers',
            data={
                'idempotencyKey': str(uuid.uuid4()),
                'source': {
                    'type': 'wallet',
                    'id': str(wallet_id),
                },
                'destination': {
                    'type': 'wallet',
                    'id': str(master_wallet_id),
                },
                'amount': {'amount': f'{amount:.2f}', 'currency': 'USD'},
            },
        )

    def create_wallet(self, idempotency_key: uuid.UUID, address: str) -> dict[str, Any]:
        return self._request(
            method='POST',
            endpoint='v1/wallets',
            data={
                'idempotencyKey': str(idempotency_key),
                'description': f'Deposit wallet for {address}',
            },
        )

    def create_address_for_wallet(self, wallet_id: str, chain: str) -> dict[str, Any]:
        return self._request(
            method='POST',
            endpoint=f'v1/wallets/{wallet_id}/addresses',
            data={
                'idempotencyKey': str(uuid.uuid4()),
                'currency': 'USD',
                'chain': chain,
            },
        )

    def get_wallet_info(self, wallet_id: str) -> dict[str, Any]:
        return self._request(
            method='GET',
            endpoint=f'v1/wallets/{wallet_id}',
        )

    def get_withdrawal_info(self, withdrawal_id: str) -> dict[str, Any]:
        return self._request(
            method='GET',
            endpoint=f'v1/transfers/{withdrawal_id}',
        )
