import math
from numbers import Real
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field
from pyproj import Geod
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon, shape

app = FastAPI(title="Farm Registry Data Tools", version="1.0.0")


class GeoJSONPayload(BaseModel):
    type: Literal["Feature", "Polygon", "MultiPolygon"]
    geometry: dict | None = None
    coordinates: list | None = None
    properties: dict = Field(default_factory=dict)


class ValidationResult(BaseModel):
    valid: bool
    area_m2: float | None = None
    issues: list[str] = Field(default_factory=list)


class Parcel(BaseModel):
    id: str
    farmer: str
    area: float
    status: Literal["Valid", "Review", "Blocked"]
    crop: str
    center: tuple[float, float]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "farm-registry-data-tools"}


@app.get("/parcels", response_model=list[Parcel])
def parcels() -> list[Parcel]:
    return [
        Parcel(
            id="MD-CT-00142",
            farmer="AgroNord SRL",
            area=42.8,
            status="Valid",
            crop="Grâu",
            center=(47.02, 28.84),
        ),
        Parcel(
            id="MD-CT-00143",
            farmer="Ion Balan",
            area=18.3,
            status="Review",
            crop="Porumb",
            center=(47.04, 28.88),
        ),
        Parcel(
            id="MD-CT-00144",
            farmer="Eco Valea Mare",
            area=64.1,
            status="Valid",
            crop="Floarea-soarelui",
            center=(46.98, 28.92),
        ),
    ]


GEOD = Geod(ellps="WGS84")


def _ring_area_m2(ring: object) -> float:
    """Return a ring's WGS84 geodesic area, in square metres."""
    coordinates = list(ring)  # type: ignore[arg-type]
    longitudes, latitudes = zip(*coordinates)
    area, _ = GEOD.polygon_area_perimeter(longitudes, latitudes)
    return abs(area)


def _polygon_area_m2(polygon: Polygon) -> float:
    shell_area = _ring_area_m2(polygon.exterior.coords)
    hole_area = sum(_ring_area_m2(ring.coords) for ring in polygon.interiors)
    return max(0.0, shell_area - hole_area)


def _geodesic_area_m2(geometry: Polygon | MultiPolygon) -> float:
    if isinstance(geometry, Polygon):
        return _polygon_area_m2(geometry)
    return sum(_polygon_area_m2(polygon) for polygon in geometry.geoms)


def _geometry_from_payload(payload: GeoJSONPayload) -> dict | None:
    if payload.type == "Feature":
        return payload.geometry
    coordinates = payload.coordinates
    if coordinates is None:
        coordinates = payload.properties.get("coordinates")
    if coordinates is None:
        return None
    return {"type": payload.type, "coordinates": coordinates}


def _validate_coordinate_ranges(value: object) -> None:
    if not isinstance(value, (list, tuple)):
        raise ValueError("coordinates must be nested arrays")
    if len(value) >= 2 and all(isinstance(item, Real) for item in value[:2]):
        longitude, latitude = value[:2]
        if not (math.isfinite(longitude) and math.isfinite(latitude)):
            raise ValueError("coordinates must be finite")
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError("coordinates must be lon/lat")
        return
    for child in value:
        _validate_coordinate_ranges(child)


@app.post("/validate/parcel", response_model=ValidationResult)
def validate_parcel(payload: GeoJSONPayload) -> ValidationResult:
    issues: list[str] = []
    geometry = _geometry_from_payload(payload)
    if not geometry or "coordinates" not in geometry:
        return ValidationResult(valid=False, issues=["geometry.coordinates is required"])
    try:
        _validate_coordinate_ranges(geometry["coordinates"])
        polygon = shape(geometry)
    except (GEOSException, TypeError, ValueError, KeyError, IndexError):
        return ValidationResult(valid=False, issues=["invalid GeoJSON geometry"])
    if not isinstance(polygon, (Polygon, MultiPolygon)):
        return ValidationResult(valid=False, issues=["geometry must be Polygon or MultiPolygon"])
    if polygon.is_empty:
        issues.append("geometry is empty")
    if not polygon.is_valid:
        issues.append("geometry has a topology issue")
    area_m2 = 0.0 if polygon.is_empty else _geodesic_area_m2(polygon)
    if area_m2 <= 0:
        issues.append("area must be greater than zero")
    return ValidationResult(valid=not issues, area_m2=round(area_m2, 4), issues=issues)
