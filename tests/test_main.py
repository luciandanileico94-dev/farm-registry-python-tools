import json

from fastapi.testclient import TestClient
from shapely.geometry import shape

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_cors_allows_vite_origins() -> None:
    response = client.get("/parcels", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin() -> None:
    response = client.get("/parcels", headers={"Origin": "https://not-farm-registry.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allows_vite_origin() -> None:
    response = client.options(
        "/parcels",
        headers={
            "Origin": "http://127.0.0.1:4173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4173"


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
    parcels = response.json()
    expected_keys = {"id", "farmer", "area", "status", "crop", "center", "geometry"}
    assert parcels
    for parcel in parcels:
        assert set(parcel) == expected_keys
        assert isinstance(parcel["id"], str)
        assert isinstance(parcel["farmer"], str)
        assert isinstance(parcel["area"], (int, float))
        assert isinstance(parcel["status"], str)
        assert parcel["status"] in {"Valid", "Review", "Blocked"}
        assert isinstance(parcel["crop"], str)
        assert isinstance(parcel["center"], list)
        assert len(parcel["center"]) == 2
        latitude, longitude = parcel["center"]
        assert isinstance(latitude, (int, float))
        assert isinstance(longitude, (int, float))
        assert -90 <= latitude <= 90
        assert -180 <= longitude <= 180
        geometry = parcel["geometry"]
        assert geometry["type"] == "Polygon"
        assert shape(geometry).is_valid
        assert not shape(geometry).is_empty
        assert geometry["coordinates"][0][0] == geometry["coordinates"][0][-1]
    assert all(parcel["id"].startswith("SYN-") for parcel in parcels)


def test_parcel_geometry_is_deterministic_and_matches_center() -> None:
    first = client.get("/parcels").json()
    second = client.get("/parcels").json()
    assert [parcel["geometry"] for parcel in first] == [parcel["geometry"] for parcel in second]

    for parcel in first:
        latitude, longitude = parcel["center"]
        centroid = shape(parcel["geometry"]).centroid
        assert abs(centroid.x - longitude) < 1e-9
        assert abs(centroid.y - latitude) < 1e-9


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


def test_rejects_coordinates_outside_lon_lat_ranges() -> None:
    response = client.post(
        "/validate/parcel",
        json={
            "type": "Polygon",
            "coordinates": [[[181, 47], [181, 48], [180, 48], [181, 47]]],
        },
    )
    assert response.json() == {
        "valid": False,
        "area_m2": None,
        "issues": ["invalid GeoJSON geometry"],
    }


def test_rejects_non_finite_coordinates() -> None:
    payload = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, float("inf")], [1, 1], [0, 0]]],
    }
    response = client.post(
        "/validate/parcel",
        content=json.dumps(payload),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["issues"] == ["invalid GeoJSON geometry"]


def test_rejects_three_dimensional_coordinates() -> None:
    response = client.post(
        "/validate/parcel",
        json={
            "type": "Polygon",
            "coordinates": [[[0, 0, 10], [1, 0, 10], [1, 1, 10], [0, 0, 10]]],
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "area_m2": None,
        "issues": ["invalid GeoJSON geometry"],
    }


def test_rejects_feature_with_missing_geometry_type() -> None:
    response = client.post(
        "/validate/parcel",
        json={"type": "Feature", "geometry": {"coordinates": []}},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["issues"] == ["geometry.type must be a string"]


def test_rejects_invalid_coordinate_structure() -> None:
    response = client.post(
        "/validate/parcel",
        json={"type": "Polygon", "coordinates": [[0, 0], [1, 1]]},
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_subtracts_polygon_holes_from_geodesic_area() -> None:
    response = client.post(
        "/validate/parcel",
        json={
            "type": "Polygon",
            "coordinates": [
                [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]],
                [[0.5, 0.5], [1.5, 0.5], [1.5, 1.5], [0.5, 1.5], [0.5, 0.5]],
            ],
        },
    )
    assert response.json()["valid"] is True
    assert response.json()["area_m2"] < 40_000_000_000


def test_sums_multipolygon_parts() -> None:
    response = client.post(
        "/validate/parcel",
        json={
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                [[[2, 0], [3, 0], [3, 1], [2, 1], [2, 0]]],
            ],
        },
    )
    assert response.json()["valid"] is True
    assert response.json()["area_m2"] > 24_000_000_000
