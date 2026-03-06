"""
WhatsApp Message Request DTO - carries inbound message data to use-cases.
"""


class WhatsAppMessageRequestDTO:
    """Data Transfer Object for inbound WhatsApp messages."""

    def __init__(
        self,
        phone: str,
        message: str,
        source: str = "twilio",
        has_media: bool = False,
    ):
        self.phone = phone
        self.message = message
        self.source = source
        self.has_media = has_media
