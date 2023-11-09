import logging

import boto3
from botocore.exceptions import ClientError

from apps.contents.choices import MediaType

from utils.constants import MAX_IMAGE_FILE_SIZE, MAX_VIDEO_FILE_SIZE


class S3Service:
    def __init__(self, access_key, secret_key, bucket):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket

    def get_pre_signed_upload_url(self, key: str, file_type: str, expiration):
        if file_type == MediaType.IMAGE:
            conditions = [['content-length-range', 0, MAX_IMAGE_FILE_SIZE]]
        else:
            conditions = [['content-length-range', 0, MAX_VIDEO_FILE_SIZE]]
        s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        response = None
        try:
            response = s3_client.generate_presigned_post(
                self.bucket,
                key,
                Fields=None,
                Conditions=conditions,
                ExpiresIn=expiration,
            )
        except ClientError:
            logging.exception('Could not generate presigned url')
        return response

    def get_pre_signed_fetch_url(self, s3_key, expiration):
        s3_client = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': s3_key},
            ExpiresIn=expiration,
        )
