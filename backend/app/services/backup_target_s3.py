from __future__ import annotations

import boto3  # type: ignore[import-untyped]

from .backup_target_base import BackupTargetHandler


class S3BackupTargetHandler(BackupTargetHandler):
    def __init__(self, config: dict):
        self.config = config

    def _client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.config.get("endpoint_url"),
            region_name=self.config.get("region"),
            aws_access_key_id=self.config.get("access_key"),
            aws_secret_access_key=self.config.get("secret_key"),
        )

    def upload(self, local_path: str, remote_subpath: str) -> str:
        client = self._client()
        bucket = self.config.get("bucket")
        key = remote_subpath.lstrip("/")
        client.upload_file(local_path, bucket, key)
        return f"s3://{bucket}/{key}"

    def download(self, location_uri: str, local_path: str) -> None:
        client = self._client()
        bucket = self.config.get("bucket")
        key = location_uri
        if location_uri.startswith("s3://"):
            key = location_uri.split("s3://", 1)[1]
            if "/" in key:
                bucket, key = key.split("/", 1)
        client.download_file(bucket, key, local_path)
