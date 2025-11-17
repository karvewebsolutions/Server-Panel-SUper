from __future__ import annotations

from typing import Any, Dict, Iterable, List

from sqlalchemy.orm import Session

from ...models.dns import DNSProviderCredential, DNSRecord, Domain
from .dns_auto_provisioner import DNSAutoProvisioner
from .dns_template_service import DNSTemplateService
from .powerdns_service import PowerDNSService
from .providers import (
    CloudflareProvider,
    DigitalOceanProvider,
    GoDaddyProvider,
    HetznerProvider,
    NamecheapProvider,
    Route53Provider,
)


class DNSManager:
    def __init__(self, db: Session):
        self.db = db
        self.powerdns = PowerDNSService()
        self.template_service = DNSTemplateService()
        self.auto_provisioner = DNSAutoProvisioner()

    def _provider_credentials(self, domain: Domain) -> Dict:
        credential: DNSProviderCredential | None = domain.provider_credential
        return credential.credentials_json if credential else {}

    def _get_provider(self, domain: Domain):
        provider_type = domain.provider_type.lower()
        credentials = self._provider_credentials(domain)
        provider_map = {
            "cloudflare": CloudflareProvider,
            "route53": Route53Provider,
            "digitalocean": DigitalOceanProvider,
            "hetzner": HetznerProvider,
            "namecheap": NamecheapProvider,
            "godaddy": GoDaddyProvider,
        }
        if provider_type == "powerdns":
            return self.powerdns
        provider_cls = provider_map.get(provider_type)
        if not provider_cls:
            raise ValueError(f"Unsupported DNS provider: {provider_type}")
        return provider_cls(credentials=credentials)

    def _persist_records(self, records: Iterable[DNSRecord]) -> List[DNSRecord]:
        saved: List[DNSRecord] = []
        for record in records:
            self.db.add(record)
            saved.append(record)
        self.db.commit()
        for record in saved:
            self.db.refresh(record)
        return saved

    def create_dns_for_deployment(
        self, app: Any, domain: Domain, subdomains: list[str] | None = None
    ) -> List[DNSRecord]:
        provider = self._get_provider(domain)
        provider.ensure_zone(domain)
        records = self.auto_provisioner.generate_app_records(app, domain, subdomains)
        persisted = self._persist_records(records)
        if isinstance(provider, PowerDNSService):
            for record in persisted:
                record.domain = domain
                provider.create_record(record)
        return persisted

    def delete_dns_for_app(self, app: Any) -> None:
        domain_id = getattr(app, "domain_id", None)
        if not domain_id:
            return
        domain = self.db.get(Domain, domain_id)
        if not domain:
            return
        provider = self._get_provider(domain)
        if isinstance(provider, PowerDNSService):
            for record in list(domain.records):
                provider.delete_record(record)
        self.db.query(DNSRecord).filter(DNSRecord.domain_id == domain.id).delete()
        self.db.commit()

    def provision_acme_dns_challenge(self, domain: Domain, token: str) -> DNSRecord:
        provider = self._get_provider(domain)
        record = self.auto_provisioner.acme_challenge_record(domain, token)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        if isinstance(provider, PowerDNSService):
            record.domain = domain
            provider.create_record(record)
        return record

    def remove_acme_dns_challenge(self, domain: Domain, token: str) -> None:
        record = (
            self.db.query(DNSRecord)
            .filter(
                DNSRecord.domain_id == domain.id,
                DNSRecord.record_type == "TXT",
                DNSRecord.name == "_acme-challenge",
                DNSRecord.value == token,
            )
            .first()
        )
        if not record:
            return
        provider = self._get_provider(domain)
        if isinstance(provider, PowerDNSService):
            record.domain = domain
            provider.delete_record(record)
        self.db.delete(record)
        self.db.commit()

    def sync_domain(self, domain_id: int) -> List[dict]:
        domain = self.db.get(Domain, domain_id)
        if not domain:
            raise ValueError(f"Domain with id {domain_id} not found")
        provider = self._get_provider(domain)
        provider.ensure_zone(domain)
        records = provider.list_records(domain) if hasattr(provider, "list_records") else []
        return records
