from app.application.services.hotel_context_service import HotelContextService


class HotelRepoStub:
    def __init__(self):
        self.called_with = None

    def get_active_hotel(self, hotel_id=None):
        self.called_with = hotel_id

        # Retorna um objeto simples com os atributos usados pelo service.
        if not hotel_id:
            return None

        policies = type(
            "Policies",
            (),
            {
                "checkin_time": "14:00",
                "checkout_time": "12:00",
                "cancellation_policy": "24h",
                "pet_policy": "pets ok",
                "child_policy": "kids ok",
                "amenities": "pool, gym",
            },
        )()

        return type(
            "Hotel",
            (),
            {
                "name": "Hotel X",
                "address": "Rua 1",
                "contact_phone": "+5511999999999",
                "policies": policies,
            },
        )()


def test_get_context_uses_hotel_id():
    repo = HotelRepoStub()
    service = HotelContextService(hotel_repository=repo)

    ctx = service.get_context("hotel-1")

    assert repo.called_with == "hotel-1"
    assert "CONTEXTO DO HOTEL" in ctx
    assert "Hotel X" in ctx

