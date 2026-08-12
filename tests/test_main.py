from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_validates_geojson_feature() -> None:
    payload = {"type":"Feature","properties":{},"geometry":{"type":"Polygon","coordinates":[[[0,0],[2,0],[2,2],[0,2],[0,0]]]}}
    response = client.post("/validate/parcel", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["area_m2"] == 4.0

def test_rejects_missing_geometry() -> None:
    response = client.post("/validate/parcel", json={"type":"Feature","properties":{}})
    assert response.status_code == 200
    assert response.json()["valid"] is False
