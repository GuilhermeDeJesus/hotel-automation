#!/usr/bin/env python3
"""
Job de No-show: marca reservas CONFIRMED como NO_SHOW quando a data de check-in passou.

Uso:
    python scripts/mark_no_show.py              # usa data de hoje
    python scripts/mark_no_show.py --date 2025-03-04  # data específica

Recomendado para cron diário (ex: 01:00):
    0 1 * * * cd /path/to/hotel-automation && python scripts/mark_no_show.py
"""
import argparse
from datetime import date

from app.infrastructure.persistence.sql.database import SessionLocal, init_db
from app.infrastructure.persistence.sql.reservation_repository_sql import (
    ReservationRepositorySQL,
)


def mark_no_show(reference_date: date | None = None) -> tuple[int, int]:
    """
    Marca reservas CONFIRMED com check-in no passado como NO_SHOW.

    Returns:
        (count_marked, count_errors)
    """
    ref = reference_date or date.today()
    init_db()
    session = SessionLocal()
    repo = ReservationRepositorySQL(session)
    # TODO: obter hotel_id do contexto/config/env
    hotel_id = os.getenv("HOTEL_ID") or "default-hotel-id"  # Ajuste conforme necessário

    try:
        reservations = repo.find_confirmed_past_checkin_date(ref, hotel_id)
        marked = 0
        errors = 0

        for reservation in reservations:
            try:
                reservation.mark_as_no_show()
                repo.save(reservation, hotel_id)
                marked += 1
                print(
                    f"  NO_SHOW: reserva {reservation.id} "
                    f"(check-in {reservation.stay_period.start if reservation.stay_period else 'N/A'})"
                )
            except Exception as e:
                errors += 1
                print(f"  ERRO reserva {reservation.id}: {e}")

        return marked, errors
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Marca reservas CONFIRMED com check-in no passado como NO_SHOW."
    )
    parser.add_argument(
        "--date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Data de referência (padrão: hoje)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Modo silencioso (apenas saída numérica)",
    )
    args = parser.parse_args()

    ref_date = date.today()
    if args.date:
        try:
            ref_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Erro: data inválida '{args.date}'. Use YYYY-MM-DD.")
            exit(1)

    if not args.quiet:
        print(f"Executando job no-show (referência: {ref_date})...")

    marked, errors = mark_no_show(ref_date)

    if args.quiet:
        print(f"{marked} {errors}")
    else:
        print(f"\nConcluído: {marked} reserva(s) marcada(s) como NO_SHOW, {errors} erro(s).")


if __name__ == "__main__":
    main()
