from __future__ import annotations

import re
from typing import Tuple


class SubdomainService:
    @staticmethod
    def normalize_domain(domain_str: str) -> str:
        """
        Normalize raw domain/subdomain strings by stripping schemes, paths and casing.
        """
        domain = domain_str.strip().lower()
        if not domain:
            return ""
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        domain = domain.split("/", 1)[0]
        domain = domain.rstrip(".")
        return domain

    @classmethod
    def split_domain(cls, domain_str: str) -> Tuple[str, str]:
        normalized = cls.normalize_domain(domain_str)
        if not normalized:
            return "", ""
        if "." not in normalized:
            return "", normalized
        parts = normalized.split(".")
        root = ".".join(parts[-2:]) if len(parts) >= 2 else normalized
        subdomain = ".".join(parts[:-2]) if len(parts) > 2 else parts[0]
        if len(parts) == 2:
            subdomain = ""
        return subdomain, root

    @staticmethod
    def generate_subdomain_from_app_name(app_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", app_name.lower()).strip("-")
        return slug or "app"

    @staticmethod
    def normalize_subdomain(subdomain: str | None) -> str:
        if not subdomain:
            return ""
        slug = re.sub(r"[^a-z0-9\.-]+", "-", subdomain.lower()).strip("-.")
        slug = re.sub(r"-{2,}", "-", slug)
        return slug

    @staticmethod
    def build_fqdn(subdomain: str, root_domain: str) -> str:
        clean_root = SubdomainService.normalize_domain(root_domain)
        clean_sub = (subdomain or "").strip().lower().strip(".")
        if not clean_sub:
            return clean_root
        return f"{clean_sub}.{clean_root}"
