from solders.pubkey import Pubkey
from solders.signature import Signature

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import TokenAuthentication

from apps.creators.models import Creator


class Web3Authentication(TokenAuthentication):
    keyword = 'Signature'

    def authenticate_credentials(self, key):  # noqa: PLR6301
        try:
            addr, sig = key.split(':')
            public_key = Pubkey.from_string(addr)
            if not public_key.is_on_curve():
                raise AuthenticationFailed(detail='Invalid address provided in signature.')

            msg = 'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app'
            signature = Signature.from_string(sig)
            if not signature.verify(public_key, msg.encode()):
                raise AuthenticationFailed('Signature provided is not valid for the address.')

            account, _ = Creator.objects.get_or_create(address=str(public_key), defaults={'address': str(public_key)})
        except Exception as e:  # noqa: BLE001
            if isinstance(e, AuthenticationFailed):
                raise

            raise AuthenticationFailed(str(e)) from e

        return account, None
