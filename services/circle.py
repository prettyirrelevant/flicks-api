import uuid
import logging
from decimal import Decimal
from typing import Any, Literal

import requests

logger = logging.getLogger(__name__)


class CircleAPI:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()

    def _request(
        self,
        method: Literal['GET', 'POST'],
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> requests.Response:
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        url = f'{self.base_url}/{endpoint}'
        try:
            response = self.session.request(method, url, params=params, json=data, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.exception('Error occurred while making request to %s with error %s', url, e.response.json())
            return None

        return response

    def ping(self) -> bool:
        response = self._request('GET', 'ping')
        return response.json().get('message') == 'pong'

    def make_withdrawal(
        self,
        amount: Decimal,
        master_wallet_id: int,
        destination_address: str,
        chain: str,
    ) -> dict[str, Any]:
        response = self._request(
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
                'amount': {'amount': str(amount), 'currency': 'USD'},
            },
        )
        return response.json()

    def create_wallet(self, idempotency_key: uuid.UUID, address: str) -> dict[str, Any]:
        response = self._request(
            method='POST',
            endpoint='v1/wallets',
            data={
                'idempotencyKey': str(idempotency_key),
                'description': f'Deposit wallet for {address}',
            },
        )
        return response.json()

    def create_address_for_wallet(self, wallet_id: str, chain: str) -> dict[str, Any]:
        response = self._request(
            method='POST',
            endpoint=f'v1/wallets/{wallet_id}/addresses',
            data={
                'idempotencyKey': str(uuid.uuid4()),
                'currency': 'USD',
                'chain': chain,
            },
        )
        return response.json()

    def get_wallet_info(self, wallet_id: str) -> dict[str, Any]:
        response = self._request(
            method='GET',
            endpoint=f'v1/wallets/{wallet_id}',
        )
        return response.json()

    def get_withdrawal_info(self, withdrawal_id: str) -> dict[str, Any]:
        response = self._request(
            method='GET',
            endpoint=f'v1/transfers/{withdrawal_id}',
        )
        return response.json()
