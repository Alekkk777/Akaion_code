import pytest

from app.agents.planner import PlannerAgent
from app.core.exceptions import PlanningError
from app.models.schemas import Workflow


@pytest.mark.asyncio
async def test_planner_creates_messaging_step():
    planner = PlannerAgent()
    workflow = Workflow(intent="invia un messaggio a Marco", context={"to": "Marco"})

    result = await planner.run(workflow)

    assert len(result.steps) == 1
    assert result.steps[0].service == "messaging"
    assert result.steps[0].action == "send_message"


@pytest.mark.asyncio
async def test_planner_creates_multiple_steps_for_combined_intent():
    planner = PlannerAgent()
    workflow = Workflow(
        intent="manda un messaggio e blocca 30 minuti in calendario",
        context={"to": "Marco"},
    )

    result = await planner.run(workflow)

    services = {step.service for step in result.steps}
    assert services == {"messaging", "calendar"}


@pytest.mark.asyncio
async def test_planner_raises_for_unknown_intent():
    planner = PlannerAgent()
    workflow = Workflow(intent="qualcosa di completamente sconosciuto", context={})

    with pytest.raises(PlanningError):
        await planner.run(workflow)
