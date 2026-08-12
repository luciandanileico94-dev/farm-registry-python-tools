from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def reset() -> None:
    response = client.post("/demo/reset")
    assert response.status_code == 200


def test_seed_counts_and_synthetic_ids() -> None:
    reset()
    assert len(client.get("/farms").json()) == 6
    assert len(client.get("/fields").json()) == 12
    assert len(client.get("/tasks").json()) == 12
    assert len(client.get("/observations").json()) == 10
    assert len(client.get("/sync/events").json()) >= 12
    for endpoint in ("/farms", "/fields", "/tasks", "/observations", "/sync/events"):
        for item in client.get(endpoint).json():
            assert item["id"].startswith("SYN-")


def test_field_and_task_filters() -> None:
    reset()
    fields = client.get("/fields", params={"farm_id": "SYN-FARM-001", "status": "Review"})
    assert fields.status_code == 200
    assert [field["id"] for field in fields.json()] == ["SYN-FIELD-002"]

    tasks = client.get("/tasks", params={"field_id": "SYN-FIELD-002", "status": "In progress"})
    assert tasks.status_code == 200
    assert [task["id"] for task in tasks.json()] == ["SYN-TASK-002"]

    observations = client.get("/observations", params={"status": "Flagged"})
    assert observations.status_code == 200
    assert len(observations.json()) == 3


def test_farm_detail_contains_its_fields() -> None:
    reset()
    response = client.get("/farms/SYN-FARM-001")
    assert response.status_code == 200
    assert response.json()["id"] == "SYN-FARM-001"
    assert {field["farm_id"] for field in response.json()["fields"]} == {"SYN-FARM-001"}


def test_create_task_validates_relationship_and_returns_shape() -> None:
    reset()
    response = client.post(
        "/tasks",
        json={
            "farm_id": "SYN-FARM-001",
            "field_id": "SYN-FIELD-001",
            "title": "Sarcină nouă de demonstrație",
            "description": "Creată în test.",
        },
    )
    assert response.status_code == 201
    task = response.json()
    assert task["id"].startswith("SYN-")
    assert {
        "id",
        "farm_id",
        "field_id",
        "title",
        "description",
        "status",
        "priority",
        "due_date",
        "created_at",
        "updated_at",
    } == set(task)

    mismatch = client.post(
        "/tasks",
        json={
            "farm_id": "SYN-FARM-001",
            "field_id": "SYN-FIELD-003",
            "title": "Relație invalidă",
        },
    )
    assert mismatch.status_code == 422


def test_observation_is_idempotent_by_client_action_id() -> None:
    reset()
    payload = {
        "field_id": "SYN-FIELD-001",
        "status": "Reviewed",
        "note": "Observație adăugată o singură dată.",
        "client_action_id": "SYN-CLIENT-ACTION-RETRY-001",
    }
    first = client.post("/observations", json=payload)
    second = client.post("/observations", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()
    assert len(client.get("/observations").json()) == 11


def test_reset_restores_deterministic_counts() -> None:
    reset()
    client.post(
        "/observations",
        json={
            "field_id": "SYN-FIELD-001",
            "note": "Schimbare temporară",
            "client_action_id": "SYN-CLIENT-ACTION-RESET-001",
        },
    )
    response = client.post("/demo/reset")
    assert response.json() == {
        "status": "reset",
        "counts": {"farms": 6, "fields": 12, "tasks": 12, "observations": 10, "sync_events": 12},
    }


def test_invalid_ids_are_safe_404s() -> None:
    reset()
    assert client.get("/farms/SYN-FARM-999").status_code == 404
    assert client.get("/fields/SYN-FIELD-999").status_code == 404
    response = client.post(
        "/observations",
        json={
            "field_id": "SYN-FIELD-999",
            "note": "Nu trebuie creată",
            "client_action_id": "SYN-ACTION-X",
        },
    )
    assert response.status_code == 404
