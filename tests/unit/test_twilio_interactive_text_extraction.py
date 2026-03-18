from app.interfaces.api.whatsapp_webhook import _extract_twilio_message_body


def test_twilio_uses_button_text_when_body_empty():
    form_data = {
        "Body": "",
        "ButtonText": "quero ver fotos",
        "ButtonPayload": "1",
        "ListItemText": "",
        "ListItemPayload": "",
    }

    assert _extract_twilio_message_body(form_data) == "quero ver fotos"


def test_twilio_uses_list_item_text_when_body_empty():
    form_data = {
        "Body": "   ",
        "ButtonText": "",
        "ButtonPayload": "",
        "ListItemText": "FOTO 2",
        "ListItemPayload": "2",
    }

    assert _extract_twilio_message_body(form_data) == "FOTO 2"

