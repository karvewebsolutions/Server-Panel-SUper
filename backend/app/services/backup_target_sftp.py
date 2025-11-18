from __future__ import annotations

import os
from pathlib import PurePosixPath

import paramiko  # type: ignore[import-untyped]

from .backup_target_base import BackupTargetHandler


class SFTPBackupTargetHandler(BackupTargetHandler):
    def __init__(self, config: dict):
        self.config = config

    def _connect(self) -> paramiko.SFTPClient:
        transport = paramiko.Transport((self.config.get("host"), int(self.config.get("port", 22))))
        transport.connect(
            username=self.config.get("username"),
            password=self.config.get("password"),
        )
        return paramiko.SFTPClient.from_transport(transport)

    def _ensure_remote_dirs(self, sftp: paramiko.SFTPClient, path: PurePosixPath) -> None:
        segments = path.parts
        current = PurePosixPath(segments[0])
        for segment in segments[1:]:
            current = current / segment
            try:
                sftp.stat(str(current))
            except FileNotFoundError:
                sftp.mkdir(str(current))

    def upload(self, local_path: str, remote_subpath: str) -> str:
        base_path = self.config.get("base_path", "/backups")
        remote_path = PurePosixPath(base_path) / remote_subpath
        sftp = self._connect()
        try:
            self._ensure_remote_dirs(sftp, remote_path.parent)
            sftp.put(local_path, str(remote_path))
        finally:
            sftp.close()
        return f"sftp://{self.config.get('host')}{remote_path}"

    def download(self, location_uri: str, local_path: str) -> None:
        base_path = self.config.get("base_path", "/backups")
        remote_path = location_uri
        if location_uri.startswith("sftp://"):
            remote_path = location_uri.split(self.config.get("host", ""), 1)[-1]
        remote_full = PurePosixPath(base_path) / remote_path.lstrip("/")
        sftp = self._connect()
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            sftp.get(str(remote_full), local_path)
        finally:
            sftp.close()
