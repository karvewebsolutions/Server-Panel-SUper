from .base import DNSProvider


class CloudflareProvider(DNSProvider):
    name = "cloudflare"

    def create_record(self, zone: str, record):
        raise NotImplementedError("Cloudflare provider not implemented yet")

    def delete_record(self, zone: str, record_id: str):
        raise NotImplementedError("Cloudflare provider not implemented yet")

    def list_records(self, zone: str):
        raise NotImplementedError("Cloudflare provider not implemented yet")


class Route53Provider(DNSProvider):
    name = "route53"

    def create_record(self, zone: str, record):
        raise NotImplementedError("Route53 provider not implemented yet")

    def delete_record(self, zone: str, record_id: str):
        raise NotImplementedError("Route53 provider not implemented yet")

    def list_records(self, zone: str):
        raise NotImplementedError("Route53 provider not implemented yet")


class DigitalOceanProvider(DNSProvider):
    name = "digitalocean"

    def create_record(self, zone: str, record):
        raise NotImplementedError("DigitalOcean provider not implemented yet")

    def delete_record(self, zone: str, record_id: str):
        raise NotImplementedError("DigitalOcean provider not implemented yet")

    def list_records(self, zone: str):
        raise NotImplementedError("DigitalOcean provider not implemented yet")


class HetznerProvider(DNSProvider):
    name = "hetzner"

    def create_record(self, zone: str, record):
        raise NotImplementedError("Hetzner provider not implemented yet")

    def delete_record(self, zone: str, record_id: str):
        raise NotImplementedError("Hetzner provider not implemented yet")

    def list_records(self, zone: str):
        raise NotImplementedError("Hetzner provider not implemented yet")


class NamecheapProvider(DNSProvider):
    name = "namecheap"

    def create_record(self, zone: str, record):
        raise NotImplementedError("Namecheap provider not implemented yet")

    def delete_record(self, zone: str, record_id: str):
        raise NotImplementedError("Namecheap provider not implemented yet")

    def list_records(self, zone: str):
        raise NotImplementedError("Namecheap provider not implemented yet")


class GoDaddyProvider(DNSProvider):
    name = "godaddy"

    def create_record(self, zone: str, record):
        raise NotImplementedError("GoDaddy provider not implemented yet")

    def delete_record(self, zone: str, record_id: str):
        raise NotImplementedError("GoDaddy provider not implemented yet")

    def list_records(self, zone: str):
        raise NotImplementedError("GoDaddy provider not implemented yet")
