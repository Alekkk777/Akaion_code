import pytest


@pytest.mark.asyncio
async def test_create_workflow_returns_202_and_id(client):
    response = await client.post(
        "/api/v1/workflows",
        json={"intent": "invia un messaggio di benvenuto", "context": {"to": "Luca", "text": "Ciao!"}},
    )

    assert response.status_code == 202
    body = response.json()
    assert "workflow_id" in body
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_get_workflow_after_creation(client):
    create_response = await client.post(
        "/api/v1/workflows",
        json={"intent": "invia un messaggio", "context": {"to": "Anna"}},
    )
    workflow_id = create_response.json()["workflow_id"]

    get_response = await client.get(f"/api/v1/workflows/{workflow_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == workflow_id


@pytest.mark.asyncio
async def test_get_unknown_workflow_returns_404(client):
    response = await client.get("/api/v1/workflows/does-not-exist")

    assert response.status_code == 404
