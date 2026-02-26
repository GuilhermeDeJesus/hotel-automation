"""
WhatsApp Message Response DTO - carries reply data back to interfaces.
"""


class WhatsAppMessageResponseDTO:
    """Data Transfer Object for outbound WhatsApp responses."""

    def __init__(self, reply: str, success: bool = True, error: str = None):
        self.reply = reply
        self.success = success
        self.error = error
