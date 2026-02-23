from sqlalchemy import Column, Integer, String, DateTime
from .database import Base

class ReservationModel(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True)
    guest_name = Column(String, nullable=False)
    guest_phone = Column(String, index=True, nullable=False)
    checkin_date = Column(DateTime)
    status = Column(String)