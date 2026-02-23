from infrastructure.persistence.sql.database import Base, engine
from infrastructure.persistence.sql.models import ReservationModel

Base.metadata.create_all(bind=engine)