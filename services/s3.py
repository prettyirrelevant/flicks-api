import logging

import boto3
from botocore.exceptions import ClientError

from django.conf import settings

from apps.contents.choices import MediaType

from utils.constants import MAX_IMAGE_FILE_SIZE, MAX_VIDEO_FILE_SIZE


def get_pre_signed_upload_url(
    bucket_name: str,
    key: str,
    file_type: str,
    expiration,
):
    if file_type == MediaType.IMAGE:
        conditions = [['content-length-range', 0, MAX_IMAGE_FILE_SIZE]]
    else:
        conditions = [['content-length-range', 0, MAX_VIDEO_FILE_SIZE]]
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    response = None
    try:
        response = s3_client.generate_presigned_post(
            bucket_name,
            key,
            Fields=None,
            Conditions=conditions,
            ExpiresIn=expiration,
        )
    except ClientError:
        logging.exception('Could not generate presigned url')
    return response
