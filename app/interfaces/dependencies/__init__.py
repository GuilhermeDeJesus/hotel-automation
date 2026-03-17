from collections.abc import Generator
import logging

from app.application.use_cases.get_saas_dashboard import GetSaaSDashboardUseCase
from app.application.use_cases.get_journey_funnel import GetJourneyFunnelUseCase
from app.infrastructure.cache.redis_repository import RedisRepository
from app.infrastructure.persistence.sql.database import SessionLocal
from app.infrastructure.persistence.sql.reservation_repository_sql import ReservationRepositorySQL
from app.infrastructure.persistence.sql.saas_repository_sql import SaaSRepositorySQL

logger = logging.getLogger(__name__)


def _get_cache_or_none():
    """Redis cache ou None se indisponível (evita 500 quando Redis está fora)."""
    try:
        return RedisRepository()
    except Exception as e:
        logger.warning("Redis indisponível, cache desativado: %s", e)
        return None


def get_saas_dashboard_use_case() -> Generator[GetSaaSDashboardUseCase, None, None]:
    """Dependency provider for GetSaaSDashboardUseCase (SaaS analytics)."""
    session = SessionLocal()
    cache = _get_cache_or_none()
    try:
        saas_repo = SaaSRepositorySQL(session)
        yield GetSaaSDashboardUseCase(saas_repository=saas_repo, cache_repository=cache)
    finally:
        session.close()


def get_journey_funnel_use_case() -> Generator[GetJourneyFunnelUseCase, None, None]:
    """Dependency provider for GetJourneyFunnelUseCase."""
    session = SessionLocal()
    try:
        saas_repo = SaaSRepositorySQL(session)
        reservation_repo = ReservationRepositorySQL(session)
        yield GetJourneyFunnelUseCase(saas_repository=saas_repo, reservation_repository=reservation_repo)
    finally:
        session.close()

