from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.exceptions import AuthenticationFailed

from .models import Creator


class CustomJWTAuthentication(JWTAuthentication):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.creator_model = Creator

    def get_user(self, validated_token):
        try:
            creator_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as e:
            raise InvalidToken('Token contained no recognizable creator identification') from e

        try:
            creator = self.creator_model.objects.get(**{api_settings.USER_ID_FIELD: creator_id})
        except self.creator_model.DoesNotExist as e:
            raise AuthenticationFailed('Creator not found') from e

        return creator

    def authenticate(self, request):
        response = super().authenticate(request)
        if response is None:
            return response

        creator, validated_token = response
        return creator, validated_token
