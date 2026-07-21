class MessagingService:
    """Mock di un connettore WhatsApp/email. Sostituire execute() con la
    chiamata reale (es. Twilio, WhatsApp Business API) senza toccare planner/executor.
    """

    async def execute(self, action: str, payload: dict) -> dict:
        if action == "send_message":
            return {
                "sent": True,
                "to": payload.get("to"),
                "text": payload.get("text"),
            }
        raise ValueError(f"Azione non supportata da MessagingService: {action}")
