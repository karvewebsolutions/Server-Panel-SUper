class BackupTargetHandler:
    def upload(self, local_path: str, remote_subpath: str) -> str:
        raise NotImplementedError

    def download(self, location_uri: str, local_path: str) -> None:
        raise NotImplementedError
