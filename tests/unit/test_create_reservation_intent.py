"""Testes para detecção de intenção de criar reserva (roteamento IA vs fluxo guiado)."""
import pytest

from app.application.use_cases.handle_whatsapp_message import HandleWhatsAppMessageUseCase


class TestCreateReservationIntent:
    """Garante que frases de reserva vão para fluxo guiado (com pagamento), não para IA."""

    def test_quanto_fica_no_total_redireciona_para_fluxo(self):
        """'quanto fica no total' deve iniciar fluxo guiado, não IA."""
        assert HandleWhatsAppMessageUseCase._is_create_reservation_intent(
            "quanto fica no total?"
        ) is True

    def test_pode_ser_o_standard_redireciona_para_fluxo(self):
        """'pode ser o Standard' deve iniciar fluxo guiado."""
        assert HandleWhatsAppMessageUseCase._is_create_reservation_intent(
            "pode ser o Standard."
        ) is True

    def test_reserva_para_redireciona_para_fluxo(self):
        """'reserva para o dia 05/04' deve iniciar fluxo guiado."""
        assert HandleWhatsAppMessageUseCase._is_create_reservation_intent(
            "qual o dia você tem de reserva para o dia 05/04?"
        ) is True

    def test_cancelar_reserva_nao_e_create_intent(self):
        """'cancelar reserva' não deve ser tratado como criar reserva."""
        assert HandleWhatsAppMessageUseCase._is_create_reservation_intent(
            "quero cancelar reserva"
        ) is False

    def test_confirmar_reserva_nao_e_create_intent(self):
        """'confirmar reserva' não deve ser tratado como criar reserva."""
        assert HandleWhatsAppMessageUseCase._is_create_reservation_intent(
            "quero confirmar reserva"
        ) is False

    def test_minha_reserva_nao_e_create_intent(self):
        """'minha reserva' deve ir para IA (consulta), não fluxo de criação."""
        assert HandleWhatsAppMessageUseCase._is_create_reservation_intent(
            "qual o status da minha reserva?"
        ) is False
