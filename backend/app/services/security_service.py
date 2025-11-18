from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..models import AlertEvent, AlertRule, SuspiciousLoginAttempt


class SecurityService:
    def __init__(self, db: Session):
        self.db = db

    def record_failed_login(self, username: str, ip: str, user_agent: Optional[str]) -> None:
        attempt = SuspiciousLoginAttempt(
            username=username,
            ip_address=ip,
            user_agent=user_agent,
            reason="invalid_password",
        )
        self.db.add(attempt)
        self.db.commit()

    def check_bruteforce(self, username: str, ip: str, window_minutes: int = 10) -> bool:
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        count = (
            self.db.query(SuspiciousLoginAttempt)
            .filter(
                SuspiciousLoginAttempt.username == username,
                SuspiciousLoginAttempt.ip_address == ip,
                SuspiciousLoginAttempt.created_at >= cutoff,
            )
            .count()
        )
        return count >= 5

    def maybe_emit_bruteforce_alert(self, username: str, ip: str) -> Optional[AlertEvent]:
        rule = (
            self.db.query(AlertRule)
            .filter(
                AlertRule.scope_type == "security",
                AlertRule.rule_type == "security_bruteforce",
                AlertRule.is_enabled.is_(True),
            )
            .first()
        )
        if not rule:
            return None
        message = f"Repeated failed login attempts for {username} from {ip}"
        event = AlertEvent(
            rule_id=rule.id,
            scope_type="security",
            scope_id=None,
            message=message,
            severity="critical",
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
