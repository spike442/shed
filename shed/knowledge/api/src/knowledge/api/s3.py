from collections.abc import Iterator

import boto3
from botocore.config import Config
from knowledge.api.config import S3Config, S3Credentials


def s3_client(config: S3Config, credentials: S3Credentials):
    addressing = Config(s3={"addressing_style": "path"})
    secret_access_key = credentials.secret_access_key.get_secret_value()
    return boto3.client(
        "s3",
        endpoint_url=config.endpoint,
        region_name=config.region,
        aws_access_key_id=credentials.access_key_id,
        aws_secret_access_key=secret_access_key,
        config=addressing,
    )


class S3KnowledgeSource:
    """Documents under ``context/<collection>/knowledge/`` in one bucket; the caller owns the S3 client."""

    def __init__(self, client, bucket: str, collection: str):
        self.client = client
        self.bucket = bucket
        self.prefix = f"context/{collection}/knowledge/"

    def list_objects(self) -> Iterator[tuple[str, str]]:
        paginator = self.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix)
        for page in pages:
            for item in page.get("Contents", []):
                key = item["Key"]
                if not key.endswith("/"):
                    yield key, item["ETag"].strip('"')

    def read_object(self, key: str) -> str:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        with response["Body"] as body:
            return body.read().decode("utf-8")
