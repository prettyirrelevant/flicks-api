from solders.pubkey import Pubkey
from solders.signature import Signature

from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import TokenAuthentication

from .models import Creator


class Web3Authentication(TokenAuthentication):
    keyword = 'Signature'

    def authenticate_credentials(self, key):
        try:
            addr, sig = key.split(':')
            public_key = Pubkey.from_string(addr)
            if not public_key.is_on_curve():
                raise AuthenticationFailed(detail='Invalid address provided in signature.')

            msg = 'Message: Welcome to Flicks!\nURI: https://flicks.vercel.app'
            signature = Signature.from_string(sig)
            if not signature.verify(public_key, msg.encode()):
                raise AuthenticationFailed('Signature provided is not valid for the address.')

            account = Creator.objects.get(address=str(public_key))
        except Exception as e:  # noqa: BLE001
            if isinstance(e, AuthenticationFailed):
                raise

            raise AuthenticationFailed(str(e)) from e

        return account, None
