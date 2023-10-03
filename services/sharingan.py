from typing import Any

from . import RequestMixin


class SharinganService(RequestMixin):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def resolve_address_to_sns(self, address: str) -> dict[str, Any]:
        response = self._request('GET', f'domain/{address}')
        return response.json()

    def fetch_collection_metadata(self, collection_address: str) -> dict[str, Any]:
        response = self._request('GET', f'collectionData/{collection_address}')
        return response.json()

    def has_nft_in_collection(self, user_address: str, collection_name: str) -> dict[str, Any]:
        response = self._request('GET', f'owner/{user_address}', params={'collectionName': collection_name})
        return response.json()
