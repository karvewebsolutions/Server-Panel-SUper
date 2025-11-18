from __future__ import annotations

import shutil
from pathlib import Path

from .backup_target_base import BackupTargetHandler


class LocalBackupTargetHandler(BackupTargetHandler):
    def __init__(self, base_path: str):
        self.base_path = base_path

    def upload(self, local_path: str, remote_subpath: str) -> str:
        destination = Path(self.base_path) / remote_subpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, destination)
        return f"local:{destination}"

    def download(self, location_uri: str, local_path: str) -> None:
        source = location_uri
        if location_uri.startswith("local:"):
            source = location_uri.split("local:", 1)[1]
        source_path = Path(source)
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            shutil.copytree(source_path, local_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, local_path)
