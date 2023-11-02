import json
from typing import Any, Optional


class MockResponse:  # pylint: disable=too-few-public-methods
    def __init__(self, status_code: int, text: str, headers: Optional[dict[str, Any]] = None) -> None:
        self.status_code = status_code
        self.text = text
        self.content = text.encode()
        self.url = 'https://i-dont-exist.com'
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return json.loads(self.text)
