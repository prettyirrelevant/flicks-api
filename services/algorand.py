from typing import Any, Optional

from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from algosdk.error import AlgodHTTPError, IndexerHTTPError


class Algorand:
    def __init__(self, algod_url: str, indexer_url: str, api_key: str) -> None:
        self.algod_client = AlgodClient(
            algod_token=api_key,
            algod_address=algod_url,
            headers={'X-API-Key': api_key},
        )
        self.indexer_client = IndexerClient(
            indexer_address=indexer_url,
            indexer_token=api_key,
            headers={'X-API-Key': api_key},
        )

    def get_transaction(self, tx_id: str) -> Optional[dict[str, Any]]:
        try:
            response = self.indexer_client.transaction(tx_id)
        except IndexerHTTPError:
            return None

        return response['transaction']

    def get_token_balance_of_address(self, token: str, address: str, decimals: int) -> Optional[int]:
        try:
            response = self.algod_client.account_asset_info(
                asset_id=int(token),
                address=address,
            )
        except AlgodHTTPError:
            return None

        if 'asset-holding' not in response:
            return None

        return response['asset-holding']['amount'] / (10**decimals)
