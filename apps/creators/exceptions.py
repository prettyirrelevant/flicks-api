from rest_framework import status
from rest_framework.exceptions import APIException


class AccountSuspensionError(Exception):
    ...


class InsufficientBalanceError(Exception):
    ...


class BadGatewayError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = 'error'
