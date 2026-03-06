#!/usr/bin/env python3
"""
6.7 Recuperação de pagamento - envia novo link para cobranças expiradas.

Uso: python scripts/payment_recovery.py [--dry-run]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Não envia, apenas lista")
    args = parser.parse_args()

    from app.infrastructure.persistence.sql.database import SessionLocal, init_db
    from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
    from app.infrastructure.persistence.sql.payment_repository_sql import PaymentRepositorySQL
    from app.infrastructure.payment.payment_provider_factory import get_payment_provider

    init_db()
    session = SessionLocal()
    payment_repo = PaymentRepositorySQL(session)
    reservation_repo = ReservationRepositorySQL(session)
    provider = get_payment_provider()

    from app.application.services.payment_recovery_service import PaymentRecoveryService
    svc = PaymentRecoveryService(
        payment_repository=payment_repo,
        reservation_repository=reservation_repo,
        payment_provider=provider,
    )

    items = svc.get_recovery_links()
    print(f"Pagamentos para recuperar: {len(items)}")
    for item in items:
        print(f"  - Reserva {item.reservation_id}: {item.phone} R$ {item.amount:.2f}")
        if item.new_checkout_url:
            print(f"    Link: {item.new_checkout_url[:50]}...")
        else:
            print("    (sem link - provider manual?)")
    if args.dry_run:
        print("Dry-run: nenhuma mensagem enviada.")
    session.close()


if __name__ == "__main__":
    main()
