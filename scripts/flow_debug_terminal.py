# -*- coding: utf-8 -*-
"""
Terminal em tempo real para debug do fluxo de conversa WhatsApp.

Exibe o estado do fluxo (action, step, dados) após cada mensagem,
para facilitar testes e compartilhar com a IA para ajustes.

Uso:
    # Com Redis/Postgres (Docker rodando):
    make up
    docker compose exec app python scripts/flow_debug_terminal.py

    # Modo standalone (in-memory, sem Redis/DB - precisa OPENAI_API_KEY):
    python scripts/flow_debug_terminal.py

Comandos durante a sessão:
    exit/quit  - encerrar
    clear      - limpar histórico e fluxo
    flow       - mostrar estado atual do fluxo (sem enviar mensagem)
"""

import json
import os
import sys
from datetime import date

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


def _format_flow_state(flow_state: dict | None) -> str:
    """Formata o flow_state para exibição legível."""
    if not flow_state:
        return "  (nenhum fluxo ativo)"
    lines = []
    for k, v in flow_state.items():
        if k == "available_rooms" and isinstance(v, list):
            lines.append(f"  {k}: [{len(v)} quartos]")
        elif isinstance(v, (dict, list)) and len(str(v)) > 60:
            lines.append(f"  {k}: {str(v)[:60]}...")
        else:
            lines.append(f"  {k}: {v}")
    return "\n".join(lines) if lines else "  (vazio)"


def _build_use_case_standalone():
    """Constrói HandleWhatsAppMessageUseCase com dependências in-memory (sem Redis/DB)."""
    from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO
    from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
    from app.application.use_cases.conversation import ConversationUseCase
    from app.application.use_cases.create_reservation import CreateReservationUseCase
    from app.application.use_cases.confirm_reservation import ConfirmReservationUseCase
    from app.application.use_cases.cancel_reservation import CancelReservationUseCase
    from app.application.use_cases.extend_reservation import ExtendReservationUseCase
    from app.application.use_cases.checkin_via_whatsapp import CheckInViaWhatsAppUseCase
    from app.application.use_cases.checkout_via_whatsapp import CheckoutViaWhatsAppUseCase
    from app.application.services.reservation_context_service import ReservationContextService
    from app.application.services.hotel_context_service import HotelContextService
    from app.domain.entities.room.room import Room
    from app.infrastructure.ai.openai_client import OpenAIClient
    from app.infrastructure.payment.manual_payment_provider import ManualPaymentProvider
    from app.infrastructure.persistence.memory.reservation_repository_memory import (
        ReservationRepositoryMemory,
    )
    from app.infrastructure.persistence.memory.payment_repository_memory import (
        PaymentRepositoryMemory,
    )

    class InMemoryCache:
        def __init__(self):
            self.store = {}

        def get(self, key):
            return self.store.get(key)

        def set(self, key, value, ttl_seconds: int = 3600):
            self.store[key] = value

        def delete(self, key):
            self.store.pop(key, None)

        def exists(self, key) -> bool:
            return key in self.store

    class RoomRepositoryMemory:
        def __init__(self):
            self._rooms = [
                Room("101", "STANDARD", 150.0, 2, "active"),
                Room("102", "STANDARD", 150.0, 2, "active"),
                Room("201", "LUXO", 280.0, 4, "active"),
            ]

        def list_all(self):
            return self._rooms

        def get_by_number(self, room_number: str):
            for r in self._rooms:
                if r.number == room_number:
                    return r
            return None

        def find_available(self, check_in, check_out, exclude_room=None):
            return [r for r in self._rooms if r.number != exclude_room]

        def is_available(self, room_number, check_in, check_out, exclude_reservation_id=None):
            return self.get_by_number(room_number) is not None

        def save(self, room):
            return room

        def deactivate(self, room_number: str):
            return True

    class HotelRepositoryMemory:
        def get_active_hotel(self):
            return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não definida em .env (necessária para ConversationUseCase)")

    cache = InMemoryCache()
    reservation_repo = ReservationRepositoryMemory()
    room_repo = RoomRepositoryMemory()
    hotel_repo = HotelRepositoryMemory()
    payment_repo = PaymentRepositoryMemory()

    ai_client = OpenAIClient(api_key=api_key)
    context_service = ReservationContextService(reservation_repo)
    hotel_context = HotelContextService(hotel_repo)

    conversation_use_case = ConversationUseCase(
        ai_service=ai_client,
        reservation_repo=reservation_repo,
        cache_repository=cache,
        context_service=context_service,
        hotel_context_service=hotel_context,
        messaging=None,
        logger=None,
    )

    create_reservation_use_case = CreateReservationUseCase(
        reservation_repository=reservation_repo,
        room_repository=room_repo,
    )

    use_case = HandleWhatsAppMessageUseCase(
        checkin_use_case=CheckInViaWhatsAppUseCase(reservation_repository=reservation_repo),
        checkout_use_case=CheckoutViaWhatsAppUseCase(reservation_repository=reservation_repo),
        cancel_reservation_use_case=CancelReservationUseCase(reservation_repository=reservation_repo),
        create_reservation_use_case=create_reservation_use_case,
        conversation_use_case=conversation_use_case,
        confirm_reservation_use_case=ConfirmReservationUseCase(reservation_repo),
        extend_reservation_use_case=ExtendReservationUseCase(
            reservation_repository=reservation_repo,
            room_repository=room_repo,
        ),
        reservation_repository=reservation_repo,
        cache_repository=cache,
        room_repository=room_repo,
        hotel_repository=hotel_repo,
        payment_provider=ManualPaymentProvider(),
        payment_repository=payment_repo,
        pre_checkin_use_case=None,
        support_ticket_use_case=None,
        room_order_use_case=None,
    )

    return use_case, cache, HandleWhatsAppMessageUseCase.FLOW_KEY_PREFIX


def _build_use_case_with_deps():
    """Constrói HandleWhatsAppMessageUseCase com dependências reais (Redis, Postgres)."""
    from app.interfaces.di_whatsapp import get_whatsapp_message_use_case
    from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase
    from app.infrastructure.cache.redis_repository import RedisRepository

    use_case = get_whatsapp_message_use_case()
    cache = RedisRepository()
    return use_case, cache, HandleWhatsAppMessageUseCase.FLOW_KEY_PREFIX


def main():
    load_dotenv()

    # Usa Redis quando REDIS_HOST está definido (ex: dentro do Docker) ou FLOW_DEBUG_USE_REDIS=1
    use_redis = (
        os.getenv("FLOW_DEBUG_USE_REDIS", "").lower() in ("1", "true", "yes")
        or bool(os.getenv("REDIS_HOST"))
    )
    phone = os.getenv("FLOW_DEBUG_PHONE", "559999900001")

    print("\n" + "=" * 72)
    print("  FLOW DEBUG TERMINAL — Fluxo de conversa em tempo real")
    print("=" * 72)
    print(f"  Telefone: {phone}")
    print(f"  Modo: {'Redis + Postgres (real)' if use_redis else 'In-memory (standalone)'}")
    print("=" * 72)
    print("  Comandos: exit/quit | clear | flow")
    print("=" * 72 + "\n")

    try:
        if use_redis:
            use_case, cache, prefix = _build_use_case_with_deps()
            flow_key = f"{prefix}{phone}"
        else:
            use_case, cache, prefix = _build_use_case_standalone()
            flow_key = f"{prefix}{phone}"
    except Exception as e:
        print(f"❌ Erro ao inicializar: {e}")
        if "OPENAI_API_KEY" in str(e):
            print("   Defina OPENAI_API_KEY no .env ou use FLOW_DEBUG_USE_REDIS=1 com Docker.")
        sys.exit(1)

    from app.application.dto.whatsapp_message_request_dto import WhatsAppMessageRequestDTO

    turn = 0

    while True:
        try:
            user_input = input("Você: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                print("\n👋 Até logo!\n")
                break

            if user_input.lower() == "clear":
                if hasattr(cache, "store"):
                    cache.store.clear()
                else:
                    cache.delete(flow_key)
                print("✅ Histórico e fluxo limpos.\n")
                continue

            if user_input.lower() == "flow":
                flow_state = cache.get(flow_key) if hasattr(cache, "get") else cache.store.get(flow_key)
                print("\n" + "-" * 72)
                print("FLOW STATE:")
                print(_format_flow_state(flow_state))
                print("-" * 72 + "\n")
                continue

            turn += 1
            print("\n⏳ Processando...", end="", flush=True)

            response_dto = use_case.execute(
                WhatsAppMessageRequestDTO(
                    phone=phone,
                    message=user_input,
                    source="terminal",
                    has_media=False,
                )
            )

            flow_state = cache.get(flow_key) if hasattr(cache, "get") else cache.store.get(flow_key)

            print("\r" + " " * 20 + "\r", end="")

            print("\n" + "-" * 72)
            print(f"TURN {turn} | FLOW STATE:")
            print(_format_flow_state(flow_state))
            print("-" * 72)
            print(f"\n🤖 Bot: {response_dto.reply}\n")

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrompido.")
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()
