import pytest

from app.agents.executor import ExecutorAgent
from app.models.schemas import TaskStep, Workflow, WorkflowStatus
from app.services.calendar import CalendarService
from app.services.messaging import MessagingService
from app.services.registry import registry


@pytest.fixture(autouse=True)
def setup_registry():
    registry.register("messaging", MessagingService())
    registry.register("calendar", CalendarService())


@pytest.mark.asyncio
async def test_executor_completes_all_steps():
    workflow = Workflow(
        intent="test",
        context={},
        steps=[TaskStep(service="messaging", action="send_message", payload={"to": "x", "text": "hi"})],
    )

    result = await ExecutorAgent().run(workflow)

    assert result.status == WorkflowStatus.COMPLETED
    assert result.steps[0].status == WorkflowStatus.COMPLETED
    assert result.steps[0].result["sent"] is True


@pytest.mark.asyncio
async def test_executor_marks_workflow_failed_on_unknown_service():
    workflow = Workflow(
        intent="test",
        context={},
        steps=[TaskStep(service="unknown", action="do", payload={})],
    )

    result = await ExecutorAgent().run(workflow)

    assert result.status == WorkflowStatus.FAILED
    assert result.steps[0].status == WorkflowStatus.FAILED
    assert result.steps[0].error is not None


@pytest.mark.asyncio
async def test_executor_stops_at_first_failed_step():
    workflow = Workflow(
        intent="test",
        context={},
        steps=[
            TaskStep(service="unknown", action="do", payload={}),
            TaskStep(service="messaging", action="send_message", payload={}),
        ],
    )

    result = await ExecutorAgent().run(workflow)

    assert result.steps[1].status == WorkflowStatus.PENDING
