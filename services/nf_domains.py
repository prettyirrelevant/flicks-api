from typing import Any

from . import RequestMixin


class NFDomains(RequestMixin):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def resolve_address(self, address: str) -> dict[str, Any]:
        return self._request('GET', 'nfd/lookup', params={'address': address, 'allowUnverified': True, 'view': 'full'})
