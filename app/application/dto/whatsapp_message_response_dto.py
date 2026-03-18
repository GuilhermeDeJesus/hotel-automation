"""
WhatsApp Message Response DTO - carries reply data back to interfaces.
"""


class WhatsAppMessageResponseDTO:
    """Data Transfer Object for outbound WhatsApp responses."""

    def __init__(
        self,
        reply: str,
        success: bool = True,
        error: str | None = None,
        message_type: str = "text",
        buttons: list[dict[str, str]] | None = None,
        list_header: str | None = None,
        list_body: str | None = None,
        list_items: list[dict] | None = None,
        media_ids: list[str] | None = None,
        media_caption: str | None = None,
    ):
        self.reply = reply
        self.success = success
        self.error = error
        self.message_type = message_type
        self.buttons = buttons or []
        self.list_header = list_header
        self.list_body = list_body
        self.list_items = list_items or []
        self.media_ids = media_ids or []
        self.media_caption = media_caption
