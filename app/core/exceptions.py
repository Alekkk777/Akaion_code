from fastapi import Request
from fastapi.responses import JSONResponse


class WorkflowNotFoundError(Exception):
    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        super().__init__(f"Workflow '{workflow_id}' non trovato")


class PlanningError(Exception):
    """Sollevata quando il Planner non riesce a scomporre l'intent in step eseguibili."""


async def workflow_not_found_handler(request: Request, exc: WorkflowNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


async def planning_error_handler(request: Request, exc: PlanningError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})
