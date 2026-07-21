from app.services.calendar import CalendarService
from app.services.messaging import MessagingService
from app.services.registry import registry


def register_services() -> None:
    registry.register("messaging", MessagingService())
    registry.register("calendar", CalendarService())
