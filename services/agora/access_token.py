import hmac
import time
import base64
import struct
import logging
import secrets
from zlib import crc32
from hashlib import sha256
from collections import OrderedDict

K_JOIN_CHANEL = 1
K_PUBLISH_AUDIO_STREAM = 2
K_PUBLISH_VIDEO_STREAM = 3
K_PUBLISH_DATA_STREAM = 4
K_RMT_LOGIN = 1000

VERSION_LENGTH = 3
APP_ID_LENGTH = 32

logger = logging.getLogger(__name__)


def get_version():
    return '006'


def pack_uint16(val):
    return struct.pack('<H', int(val))


def pack_uint32(val):
    return struct.pack('<I', int(val))


def pack_int32(val):
    return struct.pack('<i', int(val))


def pack_string(string):
    return pack_uint16(len(string)) + string


def pack_map(data):
    ret = pack_uint16(len(list(data.items())))
    for key, value in list(data.items()):
        ret += pack_uint16(key) + pack_string(value)
    return ret


def pack_map_uint32(data):
    ret = pack_uint16(len(list(data.items())))
    for key, value in list(data.items()):
        ret += pack_uint16(key) + pack_uint32(value)
    return ret


class ReadByteBuffer:
    def __init__(self, bytes_val):
        self.buffer = bytes_val
        self.position = 0

    def un_pack_uint16(self):
        struct_len = struct.calcsize('H')
        buff = self.buffer[self.position: self.position + struct_len]
        ret = struct.unpack('<H', buff)[0]
        self.position += len
        return ret

    def un_pack_uint32(self):
        struct_len = struct.calcsize('I')
        buff = self.buffer[self.position: self.position + struct_len]
        ret = struct.unpack('<I', buff)[0]
        self.position += len
        return ret

    def un_pack_string(self):
        strlen = self.un_pack_uint16()
        buff = self.buffer[self.position: self.position + strlen]
        ret = struct.unpack('<' + str(strlen) + 's', buff)[0]
        self.position += strlen
        return ret

    def un_pack_map_uint32(self):
        messages = {}
        map_len = self.un_pack_uint16()

        for _index in range(map_len):
            key = self.un_pack_uint16()
            value = self.un_pack_uint32()
            messages[key] = value
        return messages


def un_pack_content(buff):
    read_buf = ReadByteBuffer(buff)
    signature = read_buf.un_pack_string()
    crc_channel_name = read_buf.un_pack_uint32()
    crc_uid = read_buf.un_pack_uint32()
    val = read_buf.un_pack_string()

    return signature, crc_channel_name, crc_uid, val


def un_pack_messages(buff):
    read_buf = ReadByteBuffer(buff)
    salt = read_buf.un_pack_uint32()
    timestamp = read_buf.un_pack_uint32()
    messages = read_buf.un_pack_map_uint32()

    return salt, timestamp, messages


class AccessToken:
    def __init__(self, app_id='', app_certificate='', channel_name='', uid=''):
        self.app_id = app_id
        self.app_certificate = app_certificate
        self.channel_name = channel_name
        self.timestamp = int(time.time()) + 24 * 3600
        self.salt = secrets.SystemRandom().randint(1, 99999999)
        self.messages = {}
        if uid == 0:
            self.uid_str = ''
        else:
            self.uid_str = str(uid)

    def add_privilege(self, privilege, expire_timestamp):
        self.messages[privilege] = expire_timestamp

    def from_string(self, origin_token):
        dk6version = get_version()
        origin_version = origin_token[:VERSION_LENGTH]
        if origin_version != dk6version:
            return False
        origin_content = origin_token[(VERSION_LENGTH + APP_ID_LENGTH):]
        origin_content_decoded = base64.b64decode(origin_content)

        _, _, _, m_val = un_pack_content(origin_content_decoded)
        self.salt, self.timestamp, self.messages = un_pack_messages(m_val)
        return True

    def build(self):
        self.messages = OrderedDict(sorted(iter(self.messages.items()), key=lambda x: int(x[0])))

        m_val = pack_uint32(self.salt) + pack_uint32(self.timestamp) + pack_map_uint32(self.messages)

        val = self.app_id.encode('utf-8') + self.channel_name.encode('utf-8') + self.uid_str.encode('utf-8') + m_val

        signature = hmac.new(self.app_certificate.encode('utf-8'), val, sha256).digest()
        crc_channel_name = crc32(self.channel_name.encode('utf-8')) & 0xFFFFFFFF
        crc_uid = crc32(self.uid_str.encode('utf-8')) & 0xFFFFFFFF

        content = pack_string(signature) + pack_uint32(crc_channel_name) + pack_uint32(crc_uid) + pack_string(m_val)

        version = get_version()
        return version + self.app_id + base64.b64encode(content).decode('utf-8')
