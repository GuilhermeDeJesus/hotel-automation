"""Seed SaaS leads and analytics events for dashboard validation."""

from __future__ import annotations

import uuid
import sys
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.models import AnalyticsEventModel, LeadModel


def _seed_lead(session, phone: str, source: str, stage: str, message_count: int) -> None:
    existing = session.query(LeadModel).filter_by(phone_number=phone).first()
    now = datetime.now()
    if existing:
        existing.source = source
        existing.stage = stage
        existing.message_count = message_count
        existing.last_seen_at = now
        existing.updated_at = now
        return

    session.add(
        LeadModel(
            id=str(uuid.uuid4()),
            phone_number=phone,
            source=source,
            stage=stage,
            message_count=message_count,
            first_seen_at=now - timedelta(hours=2),
            last_seen_at=now,
        )
    )


def _seed_events(session, phone: str, source: str) -> None:
    now = datetime.now()
    session.add(
        AnalyticsEventModel(
            phone_number=phone,
            source=source,
            event_type="inbound_message",
            success=True,
            response_time_ms=None,
            details='{"seed": true, "direction": "in"}',
            created_at=now - timedelta(minutes=10),
        )
    )
    session.add(
        AnalyticsEventModel(
            phone_number=phone,
            source=source,
            event_type="outbound_message",
            success=True,
            response_time_ms=850,
            details='{"seed": true, "direction": "out"}',
            created_at=now - timedelta(minutes=9),
        )
    )


def seed_saas_metrics() -> None:
    session = SessionLocal()
    try:
        seeds = [
            ("5511999000001", "twilio", "NEW", 1),
            ("5511999000002", "meta", "ENGAGED", 3),
            ("5511999000003", "twilio", "RESERVATION_PENDING", 5),
            ("5511999000004", "meta", "RESERVATION_CONFIRMED", 7),
            ("5511999000005", "twilio", "CHECKED_IN", 9),
        ]

        for phone, source, stage, message_count in seeds:
            _seed_lead(session, phone, source, stage, message_count)
            _seed_events(session, phone, source)

        session.commit()
        print("Seed SaaS (leads + events) concluído.")
    finally:
        session.close()


if __name__ == "__main__":
    seed_saas_metrics()
