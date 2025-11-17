from __future__ import annotations

from typing import List

from ...models.dns import DNSRecord, Domain


class DNSTemplateService:
    def wordpress(self, domain: Domain, app: object | None = None) -> List[DNSRecord]:
        ip = getattr(app, "ipv4", "0.0.0.0") if app else "0.0.0.0"
        return [
            DNSRecord(domain=domain, record_type="A", name=domain.domain_name, value=ip),
            DNSRecord(
                domain=domain,
                record_type="CNAME",
                name="www",
                value=domain.domain_name,
            ),
        ]

    def laravel(self, domain: Domain, app: object | None = None) -> List[DNSRecord]:
        ip = getattr(app, "ipv4", "0.0.0.0") if app else "0.0.0.0"
        return [
            DNSRecord(domain=domain, record_type="A", name=domain.domain_name, value=ip),
            DNSRecord(domain=domain, record_type="TXT", name="app", value="laravel"),
        ]

    def nodejs(self, domain: Domain, app: object | None = None) -> List[DNSRecord]:
        ip = getattr(app, "ipv4", "0.0.0.0") if app else "0.0.0.0"
        return [DNSRecord(domain=domain, record_type="A", name=domain.domain_name, value=ip)]

    def email_server(self, domain: Domain, app: object | None = None) -> List[DNSRecord]:
        mail_host = getattr(app, "mail_host", f"mail.{domain.domain_name}") if app else f"mail.{domain.domain_name}"
        return [
            DNSRecord(domain=domain, record_type="MX", name=domain.domain_name, value=mail_host),
            DNSRecord(
                domain=domain,
                record_type="TXT",
                name=domain.domain_name,
                value=f"v=spf1 include:mail.{domain.domain_name} ~all",
            ),
            DNSRecord(
                domain=domain,
                record_type="TXT",
                name=f"_dmarc.{domain.domain_name}",
                value=f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain.domain_name}",
            ),
        ]

    def basic_site(self, domain: Domain, app: object | None = None) -> List[DNSRecord]:
        ip = getattr(app, "ipv4", "0.0.0.0") if app else "0.0.0.0"
        return [DNSRecord(domain=domain, record_type="A", name=domain.domain_name, value=ip)]

    def apply(self, template: str, domain: Domain, app: object | None = None) -> List[DNSRecord]:
        template_map = {
            "wordpress": self.wordpress,
            "laravel": self.laravel,
            "nodejs": self.nodejs,
            "email_server": self.email_server,
            "basic_site": self.basic_site,
        }
        handler = template_map.get(template)
        if not handler:
            raise ValueError(f"Unknown DNS template: {template}")
        return handler(domain, app)
