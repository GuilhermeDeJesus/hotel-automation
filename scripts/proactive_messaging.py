#!/usr/bin/env python3
"""
6.2 Comunicação proativa - envia mensagens automáticas.

Uso: python scripts/proactive_messaging.py [--date YYYY-MM-DD]
"""
import argparse
from datetime import date, datetime
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Data de referência (YYYY-MM-DD)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Não envia, apenas lista")
    args = parser.parse_args()

    ref_date = date.today()
    if args.date:
        ref_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    from app.infrastructure.persistence.sql.database import SessionLocal, init_db
    from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL

    init_db()
    session = SessionLocal()

    # Stub repositories - implementar find_for_proactive_messaging e ProactiveMessageLogRepository
    class StubLogRepo:
        def was_sent(self, rid, mtype, ref):
            return False
        def log_sent(self, rid, mtype):
            pass

    reservation_repo = ReservationRepositorySQL(session)
    # ProactiveMessagingService precisa de find_for_proactive_messaging
    # Por simplicidade, não adicionamos ao ReservationRepository - script é placeholder
    print(f"Proactive messaging para {ref_date} (dry_run={args.dry_run})")
    print("Implemente find_for_proactive_messaging no ReservationRepository para ativar.")
    session.close()


if __name__ == "__main__":
    main()
