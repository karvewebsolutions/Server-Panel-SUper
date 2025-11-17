from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple
from urllib import error, request

from ...core.config import get_settings
from ...models.dns import DNSRecord, Domain


class PowerDNSService:
    def __init__(self, api_url: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.api_url = api_url or "http://cp-powerdns:8081/api/v1"
        self.api_key = api_key or getattr(settings, "pdns_api_key", None)
        self.server_id = "localhost"

    @property
    def headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _request(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any] | None = None,
        allow_404: bool = False,
    ) -> Tuple[int, Dict[str, Any]]:
        data = None
        headers = self.headers
        if payload is not None:
            data = json.dumps(payload).encode()
            headers = {**headers, "Content-Type": "application/json"}
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req) as response:
                body = response.read().decode()
                return response.status, json.loads(body) if body else {}
        except error.HTTPError as exc:  # pragma: no cover - network dependent
            if allow_404 and exc.code == 404:
                return exc.code, {}
            detail = exc.read().decode()
            raise RuntimeError(
                f"PowerDNS API error {exc.code}: {detail or exc.reason}"
            ) from exc

    def _zone_name(self, domain: str | Domain) -> str:
        domain_name = domain.domain_name if isinstance(domain, Domain) else domain
        if not domain_name.endswith("."):
            domain_name = f"{domain_name}."
        return domain_name

    def ensure_zone(self, domain: str | Domain) -> Dict[str, Any]:
        zone_name = self._zone_name(domain)
        zone_url = f"{self.api_url}/servers/{self.server_id}/zones/{zone_name}"
        status_code, data = self._request("GET", zone_url, allow_404=True)
        if status_code == 404:
            payload = {
                "name": zone_name,
                "kind": "Native",
                "masters": [],
                "nameservers": [],
            }
            _, created = self._request(
                "POST",
                f"{self.api_url}/servers/{self.server_id}/zones",
                payload=payload,
            )
            return created
        return data

    def _rrset_payload(self, record: DNSRecord, changetype: str = "REPLACE") -> Dict[str, Any]:
        zone_name = self._zone_name(record.domain) if record.domain else ""
        record_name = record.name if record.name.endswith(".") else f"{record.name}."
        if record_name == ".":
            record_name = zone_name
        elif not record_name.endswith(zone_name):
            record_name = f"{record.name}.{zone_name}"
        payload = {
            "name": record_name,
            "type": record.record_type,
            "changetype": changetype,
            "ttl": record.ttl or 300,
            "records": [
                {
                    "content": record.value,
                    "disabled": False,
                }
            ],
        }
        return payload

    def create_record(self, record: DNSRecord) -> Dict[str, Any]:
        if not record.domain:
            raise ValueError("DNSRecord.domain relationship must be loaded")
        self.ensure_zone(record.domain)
        payload = {"rrsets": [self._rrset_payload(record)]}
        _, data = self._request(
            "PATCH",
            f"{self.api_url}/servers/{self.server_id}/zones/{self._zone_name(record.domain)}",
            payload=payload,
        )
        return data

    def delete_record(self, record: DNSRecord) -> Dict[str, Any]:
        if not record.domain:
            raise ValueError("DNSRecord.domain relationship must be loaded")
        payload = {"rrsets": [self._rrset_payload(record, changetype="DELETE")]}
        _, data = self._request(
            "PATCH",
            f"{self.api_url}/servers/{self.server_id}/zones/{self._zone_name(record.domain)}",
            payload=payload,
        )
        return data

    def update_record(self, record: DNSRecord) -> Dict[str, Any]:
        return self.create_record(record)

    def list_records(self, domain: str | Domain) -> List[Dict[str, Any]]:
        zone_name = self._zone_name(domain)
        _, data = self._request(
            "GET", f"{self.api_url}/servers/{self.server_id}/zones/{zone_name}"
        )
        return data.get("rrsets", [])

    def dnssec_enable(self, domain: str | Domain) -> Dict[str, Any]:
        zone_name = self._zone_name(domain)
        _, data = self._request(
            "PATCH",
            f"{self.api_url}/servers/{self.server_id}/zones/{zone_name}",
            payload={"dnssec": True},
        )
        return data

    def dnssec_disable(self, domain: str | Domain) -> Dict[str, Any]:
        zone_name = self._zone_name(domain)
        _, data = self._request(
            "PATCH",
            f"{self.api_url}/servers/{self.server_id}/zones/{zone_name}",
            payload={"dnssec": False},
        )
        return data
