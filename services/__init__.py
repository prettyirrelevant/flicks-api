import logging
import contextlib
from typing import Any, Literal, Optional

import requests

logger = logging.getLogger(__name__)


class RequestMixin:
    session = requests.Session()

    def _request(
        self,
        method: Literal['GET', 'POST'],
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Optional[requests.Response]:
        headers = {'Content-Type': 'application/json'}
        with contextlib.suppress(AttributeError):
            headers['Authorization'] = f'Bearer {self.api_key}'

        url = f'{self.base_url}/{endpoint}'
        try:
            response = self.session.request(method, url, params=params, json=data, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.exception('Error occurred while making request to %s with error %s', url, e.response.json())
            return None

        return response
