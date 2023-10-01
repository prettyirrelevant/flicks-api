import hmac
import time
import zlib
import base64
import logging
import secrets
from hashlib import sha256
from typing import ClassVar
from collections import OrderedDict

from .packer import (
    pack_int16,
    pack_string,
    pack_uint16,
    pack_uint32,
    unpack_int16,
    unpack_string,
    unpack_uint16,
    unpack_uint32,
    pack_map_uint32,
    unpack_map_uint32,
)

K_JOIN_CHANEL = 1
K_PUBLISH_AUDIO_STREAM = 2
K_PUBLISH_VIDEO_STREAM = 3
K_PUBLISH_DATA_STREAM = 4
K_RMT_LOGIN = 1000

VERSION_LENGTH = 3
APP_ID_LENGTH = 32

logger = logging.getLogger(__name__)


def get_version():
    return '007'


class Service:
    def __init__(self, service_type):
        self.__type = service_type
        self.__privileges = {}

    def __pack_type(self):
        return pack_uint16(self.__type)

    def __pack_privileges(self):
        privileges = OrderedDict(sorted(iter(self.__privileges.items()), key=lambda x: int(x[0])))
        return pack_map_uint32(privileges)

    def add_privilege(self, privilege, expire):
        self.__privileges[privilege] = expire

    def service_type(self):
        return self.__type

    def pack(self):
        return self.__pack_type() + self.__pack_privileges()

    def unpack(self, buffer):
        self.__privileges, buffer = unpack_map_uint32(buffer)
        return buffer


class ServiceRtc(Service):
    K_SERVICE_TYPE = 1

    K_PRIVILEGE_JOIN_CHANNEL = 1
    K_PRIVILEGE_PUBLISH_AUDIO_STREAM = 2
    K_PRIVILEGE_PUBLISH_VIDEO_STREAM = 3
    K_PRIVILEGE_PUBLISH_DATA_STREAM = 4

    def __init__(self, channel_name='', uid=0):
        super().__init__(ServiceRtc.K_SERVICE_TYPE)
        self.__channel_name = channel_name.encode('utf-8')
        self.__uid = b'' if uid == 0 else str(uid).encode('utf-8')

    def pack(self):
        return super().pack() + pack_string(self.__channel_name) + pack_string(self.__uid)

    def unpack(self, buffer):
        buffer = super().unpack(buffer)
        self.__channel_name, buffer = unpack_string(buffer)
        self.__uid, buffer = unpack_string(buffer)
        return buffer


class ServiceRtm(Service):
    K_SERVICE_TYPE = 2

    K_PRIVILEGE_LOGIN = 1

    def __init__(self, user_id=''):
        super().__init__(ServiceRtm.K_SERVICE_TYPE)
        self.__user_id = user_id.encode('utf-8')

    def pack(self):
        return super().pack() + pack_string(self.__user_id)

    def unpack(self, buffer):
        buffer = super().unpack(buffer)
        self.__user_id, buffer = unpack_string(buffer)
        return buffer


class ServiceFpa(Service):
    K_SERVICE_TYPE = 4

    K_PRIVILEGE_LOGIN = 1

    def __init__(self):
        super().__init__(ServiceFpa.K_SERVICE_TYPE)

    def pack(self):  # pylint: disable=W0246
        return super().pack()

    def unpack(self, buffer):  # pylint: disable=W0246
        return super().unpack(buffer)


class ServiceChat(Service):
    K_SERVICE_TYPE = 5

    K_PRIVILEGE_USER = 1
    K_PRIVILEGE_APP = 2

    def __init__(self, user_id=''):
        super().__init__(ServiceChat.K_SERVICE_TYPE)
        self.__user_id = user_id.encode('utf-8')

    def pack(self):
        return super().pack() + pack_string(self.__user_id)

    def unpack(self, buffer):
        buffer = super().unpack(buffer)
        self.__user_id, buffer = unpack_string(buffer)
        return buffer


class ServiceEducation(Service):
    K_SERVICE_TYPE = 7

    K_PRIVILEGE_ROOM_USER = 1
    K_PRIVILEGE_USER = 2
    K_PRIVILEGE_APP = 3

    def __init__(self, room_uuid='', user_uuid='', role=-1):
        super().__init__(ServiceEducation.K_SERVICE_TYPE)
        self.__room_uuid = room_uuid.encode('utf-8')
        self.__user_uuid = user_uuid.encode('utf-8')
        self.__role = role

    def pack(self):
        return super().pack() + pack_string(self.__room_uuid) + pack_string(self.__user_uuid) + pack_int16(self.__role)

    def unpack(self, buffer):
        buffer = super().unpack(buffer)
        self.__room_uuid, buffer = unpack_string(buffer)
        self.__user_uuid, buffer = unpack_string(buffer)
        self.__role, buffer = unpack_int16(buffer)
        return buffer


class AccessToken:
    K_SERVICES: ClassVar = {
        ServiceRtc.K_SERVICE_TYPE: ServiceRtc,
        ServiceRtm.K_SERVICE_TYPE: ServiceRtm,
        ServiceFpa.K_SERVICE_TYPE: ServiceFpa,
        ServiceChat.K_SERVICE_TYPE: ServiceChat,
        ServiceEducation.K_SERVICE_TYPE: ServiceEducation,
    }

    def __init__(self, app_id='', app_certificate='', issue_ts=0, expire=900):
        self.__app_id = app_id
        self.__app_cert = app_certificate

        self.__issue_ts = issue_ts if issue_ts != 0 else int(time.time())
        self.__expire = expire
        self.__salt = secrets.SystemRandom().randint(1, 99999999)

        self.__service = {}

    def __signing(self):
        signing = hmac.new(pack_uint32(self.__issue_ts), self.__app_cert, sha256).digest()
        return hmac.new(pack_uint32(self.__salt), signing, sha256).digest()

    def __build_check(self):
        def is_uuid(data):
            if len(data) != 32:  # noqa: PLR2004
                return False
            try:
                bytes.fromhex(data)
            except ValueError:
                return False
            return True

        if not is_uuid(self.__app_id) or not is_uuid(self.__app_cert):
            return False
        if not self.__service:
            return False
        return True

    def add_service(self, service):
        self.__service[service.service_type()] = service

    def build(self):
        if not self.__build_check():
            return ''

        self.__app_id = self.__app_id.encode('utf-8')
        self.__app_cert = self.__app_cert.encode('utf-8')
        signing = self.__signing()
        signing_info = (
            pack_string(self.__app_id)
            + pack_uint32(self.__issue_ts)
            + pack_uint32(self.__expire)
            + pack_uint32(self.__salt)
            + pack_uint16(len(self.__service))
        )

        for service in self.__service.values():
            signing_info += service.pack()

        signature = hmac.new(signing, signing_info, sha256).digest()

        return get_version() + base64.b64encode(zlib.compress(pack_string(signature) + signing_info)).decode('utf-8')

    def from_string(self, origin_token):
        origin_version = origin_token[:VERSION_LENGTH]
        if origin_version != get_version():
            return False

        buffer = zlib.decompress(base64.b64decode(origin_token[VERSION_LENGTH:]))
        _, buffer = unpack_string(buffer)
        self.__app_id, buffer = unpack_string(buffer)
        self.__issue_ts, buffer = unpack_uint32(buffer)
        self.__expire, buffer = unpack_uint32(buffer)
        self.__salt, buffer = unpack_uint32(buffer)
        service_count, buffer = unpack_uint16(buffer)

        for _i in range(service_count):
            service_type, buffer = unpack_uint16(buffer)
            service = AccessToken.K_SERVICES[service_type]()
            buffer = service.unpack(buffer)
            self.__service[service_type] = service
        return True
