from enum import Enum

from .access_token import (
    K_JOIN_CHANEL,
    K_PUBLISH_DATA_STREAM,
    K_PUBLISH_AUDIO_STREAM,
    K_PUBLISH_VIDEO_STREAM,
    AccessToken,
)


class Role(Enum):
    PUBLISHER = 1
    SUBSCRIBER = 2


class RtcTokenBuilder:
    @staticmethod
    def build_token_with_uid(
        app_id,
        app_certificate,
        channel_name,
        uid,
        role: Role,
        privilege_expired_ts,
    ):  # pylint: disable=R0913
        """
        app_id: The App ID issued to you by Agora. Apply for a new App ID from
            Agora Dashboard if it is missing from your kit. See Get an App ID.
        app_certificate:	Certificate of the application that you registered in
                         the Agora Dashboard. See Get an App Certificate.
        channel_name:Unique channel name for the AgoraRTC session in the string format
        uid: User ID. A 32-bit unsigned integer with a value ranging from
             1 to (2^32-1). optionalUid must be unique.
        role: Publisher = 1: A broadcaster (host) in a live-broadcast profile.
              Subscriber = 2: (Default) A audience in a live-broadcast profile.
        privilege_expire_ts: represented by the number of seconds elapsed since
                           1/1/1970. If, for example, you want to access the
                           Agora Service within 10 minutes after the token is
                           generated, set expireTimestamp as the current
                           timestamp + 600 (seconds)./
        """
        return RtcTokenBuilder.build_token_with_account(
            app_id,
            app_certificate,
            channel_name,
            uid,
            role,
            privilege_expired_ts,
        )

    @staticmethod
    def build_token_with_account(
        app_id,
        app_certificate,
        channel_name,
        account,
        role,
        privilege_expired_ts,
    ):  # pylint: disable=R0913
        """
        app_id: The App ID issued to you by Agora. Apply for a new App ID from
               Agora Dashboard if it is missing from your kit. See Get an App ID.
        app_certificate:	Certificate of the application that you registered in
                         the Agora Dashboard. See Get an App Certificate.
        channel_name:Unique channel name for the AgoraRTC session in the string format
        account: The user account string.
        role: Publisher = 1: A broadcaster (host) in a live-broadcast profile.
              Subscriber = 2: (Default) A audience in a live-broadcast profile.
        privilege_expire_ts: represented by the number of seconds elapsed since
                           1/1/1970. If, for example, you want to access the
                           Agora Service within 10 minutes after the token is
                           generated, set expireTimestamp as the current
        """
        token = AccessToken(app_id, app_certificate, channel_name, account)
        token.add_privilege(K_JOIN_CHANEL, privilege_expired_ts)
        if role == Role.PUBLISHER:
            token.add_privilege(K_PUBLISH_VIDEO_STREAM, privilege_expired_ts)
            token.add_privilege(K_PUBLISH_AUDIO_STREAM, privilege_expired_ts)
            token.add_privilege(K_PUBLISH_DATA_STREAM, privilege_expired_ts)
        return token.build()
