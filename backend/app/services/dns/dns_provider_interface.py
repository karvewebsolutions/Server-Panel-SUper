class DNSProviderInterface:
    """Abstract interface all DNS providers must implement."""

    def create_record(self, *args, **kwargs):
        raise NotImplementedError("create_record must be implemented by provider")

    def delete_record(self, *args, **kwargs):
        raise NotImplementedError("delete_record must be implemented by provider")

    def update_record(self, *args, **kwargs):
        raise NotImplementedError("update_record must be implemented by provider")

    def list_records(self, *args, **kwargs):
        raise NotImplementedError("list_records must be implemented by provider")

    def verify_record(self, *args, **kwargs):
        raise NotImplementedError("verify_record must be implemented by provider")

    def ensure_zone(self, *args, **kwargs):
        raise NotImplementedError("ensure_zone must be implemented by provider")

    def apply_template(self, *args, **kwargs):
        raise NotImplementedError("apply_template must be implemented by provider")
