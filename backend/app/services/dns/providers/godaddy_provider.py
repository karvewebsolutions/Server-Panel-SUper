from ..dns_provider_interface import DNSProviderInterface


class GoDaddyProvider(DNSProviderInterface):
    name = "godaddy"

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    def create_record(self, *args, **kwargs):
        raise NotImplementedError("GoDaddy provider integration pending")

    def delete_record(self, *args, **kwargs):
        raise NotImplementedError("GoDaddy provider integration pending")

    def update_record(self, *args, **kwargs):
        raise NotImplementedError("GoDaddy provider integration pending")

    def list_records(self, *args, **kwargs):
        raise NotImplementedError("GoDaddy provider integration pending")

    def verify_record(self, *args, **kwargs):
        raise NotImplementedError("GoDaddy provider integration pending")

    def ensure_zone(self, *args, **kwargs):
        raise NotImplementedError("GoDaddy provider integration pending")

    def apply_template(self, *args, **kwargs):
        raise NotImplementedError("GoDaddy provider integration pending")
