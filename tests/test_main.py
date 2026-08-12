from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_validates_geojson_feature() -> None:
    payload = {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
        },
    }
    response = client.post("/validate/parcel", json=payload)
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["area_m2"] > 49_000_000_000
    assert response.json()["area_m2"] < 50_000_000_000


def test_get_parcels_keeps_web_client_contract() -> None:
    response = client.get("/parcels")
    assert response.status_code == 200
    assert {"id", "farmer", "area", "status", "crop", "center"} <= response.json()[0].keys()


def test_rejects_missing_geometry() -> None:
    response = client.post("/validate/parcel", json={"type": "Feature", "properties": {}})
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_rejects_non_polygon_geometry() -> None:
    response = client.post(
        "/validate/parcel",
        json={"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}},
    )
    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "area_m2": None,
        "issues": ["geometry must be Polygon or MultiPolygon"],
    }


def test_accepts_direct_polygon_geojson() -> None:
    response = client.post(
        "/validate/parcel",
        json={
            "type": "Polygon",
            "coordinates": [
                [[28, 47], [28.001, 47], [28.001, 47.001], [28, 47.001], [28, 47]]
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["area_m2"] > 7_000
