import math
import os
from numbers import Real
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from pyproj import Geod
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon, shape

app = FastAPI(title="Farm Registry Data Tools", version="1.0.0")

_DEFAULT_CORS_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://localhost:5173",
    "http://localhost:4173",
}
_cors_origins = {
    origin.strip()
    for origin in os.getenv("FARM_REGISTRY_CORS_ORIGINS", "").split(",")
    if origin.strip()
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_cors_origins or _DEFAULT_CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class GeoJSONPayload(BaseModel):
    type: Literal["Feature", "Polygon", "MultiPolygon"]
    geometry: dict | None = None
    coordinates: list | None = None
    properties: dict = Field(default_factory=dict)


class ValidationResult(BaseModel):
    valid: bool
    area_m2: float | None = None
    issues: list[str] = Field(default_factory=list)


class ParcelGeometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[list[tuple[float, float]]]

    @model_validator(mode="after")
    def validate_polygon(self) -> "ParcelGeometry":
        polygon = shape(self.model_dump())
        if not isinstance(polygon, Polygon) or polygon.is_empty or not polygon.is_valid:
            raise ValueError("parcel geometry must be a valid, non-empty Polygon")
        return self


class Parcel(BaseModel):
    id: str
    farmer: str
    area: float
    status: Literal["Valid", "Review", "Blocked"]
    crop: str
    center: tuple[float, float]
    geometry: ParcelGeometry


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "farm-registry-data-tools"}


@app.get("/parcels", response_model=list[Parcel])
def parcels() -> list[Parcel]:
    return [
        Parcel(
            id="SYN-DEMO-001",
            farmer="Demo Fermier Exemplu",
            area=42.8,
            status="Valid",
            crop="Grâu",
            center=(47.02, 28.84),
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [28.835, 47.015],
                        [28.845, 47.015],
                        [28.845, 47.025],
                        [28.835, 47.025],
                        [28.835, 47.015],
                    ]
                ],
            },
        ),
        Parcel(
            id="SYN-DEMO-002",
            farmer="Exemplu Fermier Demo",
            area=18.3,
            status="Review",
            crop="Porumb",
            center=(47.04, 28.88),
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [28.874, 47.034],
                        [28.886, 47.034],
                        [28.886, 47.046],
                        [28.874, 47.046],
                        [28.874, 47.034],
                    ]
                ],
            },
        ),
        Parcel(
            id="SYN-DEMO-003",
            farmer="Demo Exploatație Exemplu",
            area=64.1,
            status="Valid",
            crop="Floarea-soarelui",
            center=(46.98, 28.92),
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [28.912, 46.972],
                        [28.928, 46.972],
                        [28.928, 46.988],
                        [28.912, 46.988],
                        [28.912, 46.972],
                    ]
                ],
            },
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
    if len(value) == 2 and all(
        isinstance(item, Real) and not isinstance(item, bool) for item in value
    ):
        longitude, latitude = value
        if not (math.isfinite(longitude) and math.isfinite(latitude)):
            raise ValueError("coordinates must be finite")
        if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
            raise ValueError("coordinates must be lon/lat")
        return
    if any(isinstance(item, Real) for item in value):
        raise ValueError("only 2D coordinates are supported")
    for child in value:
        _validate_coordinate_ranges(child)


@app.post("/validate/parcel", response_model=ValidationResult)
def validate_parcel(payload: GeoJSONPayload) -> ValidationResult:
    issues: list[str] = []
    geometry = _geometry_from_payload(payload)
    if not geometry or "coordinates" not in geometry:
        return ValidationResult(valid=False, issues=["geometry.coordinates is required"])
    if not isinstance(geometry.get("type"), str):
        return ValidationResult(valid=False, issues=["geometry.type must be a string"])
    try:
        _validate_coordinate_ranges(geometry["coordinates"])
        polygon = shape(geometry)
        if not isinstance(polygon, (Polygon, MultiPolygon)):
            return ValidationResult(
                valid=False, issues=["geometry must be Polygon or MultiPolygon"]
            )
        if polygon.is_empty:
            issues.append("geometry is empty")
        if not polygon.is_valid:
            issues.append("geometry has a topology issue")
        area_m2 = 0.0 if polygon.is_empty else _geodesic_area_m2(polygon)
    except (GEOSException, TypeError, ValueError, KeyError, IndexError, ArithmeticError):
        return ValidationResult(valid=False, issues=["invalid GeoJSON geometry"])
    if area_m2 <= 0:
        issues.append("area must be greater than zero")
    return ValidationResult(valid=not issues, area_m2=round(area_m2, 4), issues=issues)
