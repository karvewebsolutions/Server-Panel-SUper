from __future__ import annotations

from typing import Any, List

from ...models.dns import DNSRecord, Domain
from .dns_template_service import DNSTemplateService


class DNSAutoProvisioner:
    def __init__(self):
        self.template_service = DNSTemplateService()

    def generate_base_records(
        self, domain: Domain, subdomains: list[str] | None = None, app: Any | None = None
    ) -> List[DNSRecord]:
        subdomains = subdomains or []
        ipv4 = getattr(app, "ipv4", "0.0.0.0") if app else "0.0.0.0"
        ipv6 = getattr(app, "ipv6", None)
        records: List[DNSRecord] = [
            DNSRecord(domain=domain, record_type="A", name=domain.domain_name, value=ipv4),
        ]
        if ipv6:
            records.append(
                DNSRecord(domain=domain, record_type="AAAA", name=domain.domain_name, value=ipv6)
            )
        for sub in subdomains:
            records.append(
                DNSRecord(
                    domain=domain,
                    record_type="CNAME",
                    name=sub,
                    value=domain.domain_name,
                )
            )
        return records

    def generate_email_records(self, domain: Domain, app: Any | None = None) -> List[DNSRecord]:
        return self.template_service.email_server(domain, app)

    def generate_app_records(
        self, app: Any, domain: Domain, subdomains: list[str] | None = None
    ) -> List[DNSRecord]:
        records = self.generate_base_records(domain, subdomains=subdomains, app=app)
        if getattr(app, "email_enabled", False):
            records.extend(self.generate_email_records(domain, app))
        if getattr(app, "template", None):
            records.extend(self.template_service.apply(app.template, domain, app))
        return records

    def acme_challenge_record(self, domain: Domain, token: str) -> DNSRecord:
        return DNSRecord(
            domain=domain,
            record_type="TXT",
            name="_acme-challenge",
            value=token,
            ttl=60,
        )
