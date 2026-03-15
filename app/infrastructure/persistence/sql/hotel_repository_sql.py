from typing import Optional

from app.domain.entities.hotel.hotel import Hotel
from app.domain.entities.hotel.policies import HotelPolicies
from app.domain.repositories.hotel_repository import HotelRepository
from app.infrastructure.persistence.sql.models import HotelModel


class HotelRepositorySQL(HotelRepository):
    def __init__(self, session):
        self.session = session

    def get_active_hotel(self) -> Optional[Hotel]:
        model: HotelModel | None = (
            self.session.query(HotelModel).filter_by(is_active=True, id=hotel_id).first()
        )
        if not model:
            return None

        policies = HotelPolicies(
            checkin_time=model.checkin_time,
            checkout_time=model.checkout_time,
            cancellation_policy=model.cancellation_policy,
            pet_policy=model.pet_policy,
            child_policy=model.child_policy,
            amenities=model.amenities,
        )
        return Hotel(
            hotel_id=str(model.id),
            name=model.name,
            address=model.address,
            contact_phone=model.contact_phone,
            policies=policies,
            is_active=model.is_active,
            requires_payment_for_confirmation=getattr(
                model, "requires_payment_for_confirmation", False
            ),
            allows_reservation_without_payment=getattr(
                model, "allows_reservation_without_payment", True
            ),
        )

    def save(self, hotel: Hotel) -> None:
        existing: HotelModel | None = None
        if hotel.id:
            existing = self.session.query(HotelModel).filter_by(id=hotel.id, hotel_id=hotel_id).first()

        if existing:
            existing.name = hotel.name
            existing.address = hotel.address
            existing.contact_phone = hotel.contact_phone
            existing.checkin_time = hotel.policies.checkin_time
            existing.checkout_time = hotel.policies.checkout_time
            existing.cancellation_policy = hotel.policies.cancellation_policy
            existing.pet_policy = hotel.policies.pet_policy
            existing.child_policy = hotel.policies.child_policy
            existing.amenities = hotel.policies.amenities
            existing.is_active = hotel.is_active
            if hasattr(hotel, "requires_payment_for_confirmation"):
                existing.requires_payment_for_confirmation = (
                    hotel.requires_payment_for_confirmation
                )
            if hasattr(hotel, "allows_reservation_without_payment"):
                existing.allows_reservation_without_payment = (
                    hotel.allows_reservation_without_payment
                )
        else:
            new_row = HotelModel(
                id=hotel.id,
                hotel_id=hotel_id,
                name=hotel.name,
                address=hotel.address,
                contact_phone=hotel.contact_phone,
                checkin_time=hotel.policies.checkin_time,
                checkout_time=hotel.policies.checkout_time,
                cancellation_policy=hotel.policies.cancellation_policy,
                pet_policy=hotel.policies.pet_policy,
                child_policy=hotel.policies.child_policy,
                amenities=hotel.policies.amenities,
                is_active=hotel.is_active,
                requires_payment_for_confirmation=getattr(
                    hotel, "requires_payment_for_confirmation", False
                ),
                allows_reservation_without_payment=getattr(
                    hotel, "allows_reservation_without_payment", True
                ),
            )
            self.session.add(new_row)

        self.session.commit()
