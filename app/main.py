from fastapi import FastAPI

from app.api.v1 import workflows
from app.core.config import settings
from app.core.exceptions import (
    PlanningError,
    WorkflowNotFoundError,
    planning_error_handler,
    workflow_not_found_handler,
)
from app.core.logging import configure_logging
from app.services.bootstrap import register_services

configure_logging()
register_services()

app = FastAPI(
    title="Akaion LifeOS — Task Workflow Execution API",
    description=(
        "Servizio che riceve intent utente in linguaggio naturale, li scompone "
        "in workflow multi-step tramite un Planner agent e li esegue tramite "
        "un Executor agent che orchestra service modulari (messaging, calendar, ...)."
    ),
    version="0.1.0",
)

app.add_exception_handler(WorkflowNotFoundError, workflow_not_found_handler)
app.add_exception_handler(PlanningError, planning_error_handler)

app.include_router(workflows.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "environment": settings.environment}
