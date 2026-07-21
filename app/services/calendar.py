class CalendarService:
    """Mock di un connettore calendario (es. Google Calendar API)."""

    async def execute(self, action: str, payload: dict) -> dict:
        if action == "create_event":
            return {
                "created": True,
                "title": payload.get("title", "Nuovo evento"),
                "start": payload.get("start"),
                "duration_minutes": payload.get("duration_minutes", 30),
            }
        raise ValueError(f"Azione non supportata da CalendarService: {action}")
