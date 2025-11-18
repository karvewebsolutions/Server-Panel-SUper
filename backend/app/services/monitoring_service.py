from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import AlertEvent, AlertRule, AppInstance, Server, ServerMetricSnapshot, User

DEFAULT_THRESHOLDS = {
    "cpu_high": 90.0,
    "memory_high": 90.0,
    "disk_high": 90.0,
}


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db

    def _get_default_creator_id(self) -> Optional[int]:
        user = (
            self.db.query(User)
            .filter(User.is_active.is_(True))
            .order_by(User.id.asc())
            .first()
        )
        if user:
            return user.id
        return None

    def _resolve_rule(
        self, scope_type: str, rule_type: str, scope_id: Optional[int]
    ) -> Optional[AlertRule]:
        rule = (
            self.db.query(AlertRule)
            .filter(
                AlertRule.scope_type == scope_type,
                AlertRule.rule_type == rule_type,
                AlertRule.is_enabled.is_(True),
                AlertRule.scope_id == scope_id,
            )
            .first()
        )
        if rule:
            return rule
        return (
            self.db.query(AlertRule)
            .filter(
                AlertRule.scope_type == scope_type,
                AlertRule.rule_type == rule_type,
                AlertRule.is_enabled.is_(True),
                AlertRule.scope_id.is_(None),
            )
            .first()
        )

    def _create_event(
        self,
        rule: AlertRule,
        scope_type: str,
        scope_id: Optional[int],
        message: str,
        severity: str = "warning",
    ) -> AlertEvent:
        event = AlertEvent(
            rule_id=rule.id,
            scope_type=scope_type,
            scope_id=scope_id,
            message=message,
            severity=severity,
        )
        self.db.add(event)
        return event

    def evaluate_server_metrics(
        self, server: Server, metrics: ServerMetricSnapshot
    ) -> List[AlertEvent]:
        events: List[AlertEvent] = []
        checks = [
            ("cpu_high", metrics.cpu_percent, "CPU"),
            ("memory_high", metrics.memory_percent, "Memory"),
            ("disk_high", metrics.disk_percent, "Disk"),
        ]
        for rule_type, value, label in checks:
            rule = self._resolve_rule("server", rule_type, server.id)
            threshold = rule.threshold_value if rule else DEFAULT_THRESHOLDS.get(rule_type)
            if threshold is None:
                continue
            if value >= threshold:
                message = f"{label} usage high on {server.name}: {value:.1f}% (threshold {threshold:.1f}%)"
                selected_rule = rule
                if not selected_rule:
                    creator_id = self._get_default_creator_id()
                    if creator_id is None:
                        continue
                    selected_rule = AlertRule(
                        name=f"Default {label} threshold",
                        scope_type="server",
                        scope_id=server.id,
                        rule_type=rule_type,
                        threshold_value=threshold,
                        created_by_user_id=creator_id,
                        is_enabled=True,
                    )
                    self.db.add(selected_rule)
                    self.db.flush()
                events.append(
                    self._create_event(
                        selected_rule,
                        scope_type="server",
                        scope_id=server.id,
                        message=message,
                        severity="critical" if value >= threshold + 5 else "warning",
                    )
                )
        if events:
            self.db.commit()
            for event in events:
                self.db.refresh(event)
        return events

    def evaluate_app_instance(self, app_instance: AppInstance) -> List[AlertEvent]:
        events: List[AlertEvent] = []
        if app_instance.status in {"error", "stopped"}:
            rule = self._resolve_rule("app_instance", "app_down", app_instance.id)
            if rule and rule.is_enabled:
                message = f"Application instance {app_instance.display_name} is {app_instance.status}"
                events.append(
                    self._create_event(
                        rule,
                        scope_type="app_instance",
                        scope_id=app_instance.id,
                        message=message,
                        severity="critical",
                    )
                )
        if events:
            self.db.commit()
            for event in events:
                self.db.refresh(event)
        return events

    def evaluate_ssl_expiry(self) -> List[AlertEvent]:
        events: List[AlertEvent] = []
        soon_cutoff = datetime.utcnow() + timedelta(days=10)
        rules = (
            self.db.query(AlertRule)
            .filter(
                AlertRule.rule_type == "ssl_expiring",
                AlertRule.is_enabled.is_(True),
            )
            .all()
        )
        for rule in rules:
            # TODO: implement certificate lookup and expiry evaluation.
            # Placeholder to demonstrate hook without generating noisy events.
            _ = soon_cutoff
            _ = rule
            continue
        return events

    def get_recent_alerts(self, limit: int = 50) -> List[AlertEvent]:
        return (
            self.db.query(AlertEvent)
            .order_by(AlertEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    def acknowledge_alert(self, alert_id: int) -> AlertEvent:
        alert = self.db.get(AlertEvent, alert_id)
        if not alert:
            raise ValueError("Alert not found")
        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
