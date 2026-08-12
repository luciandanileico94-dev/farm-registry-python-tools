import math
import os
from numbers import Real
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import Field as PydanticField
from pyproj import Geod
from shapely.errors import GEOSException
from shapely.geometry import MultiPolygon, Polygon, shape

from app.repository import demo_repository, reset_demo_data


app = FastAPI(
    title="Registrul Fermelor — API demo sintetic",
    version="1.1.0",
    description=(
        "Strat de date FastAPI pentru prototipul Farm Registry Web și Mobile. "
        "Toate datele sunt sintetice, locale și identificabile prin prefixul SYN-. "
        "Serviciul nu este conectat la registre reale sau la servicii externe."
    ),
    openapi_tags=[
        {"name": "Sănătate", "description": "Verificarea disponibilității API-ului."},
        {"name": "Registru", "description": "Ferme, câmpuri și contractul legacy pentru Web."},
        {
            "name": "Activitate",
            "description": "Sarcini și observații partajate între Web și Mobile.",
        },
        {"name": "Sincronizare", "description": "Evenimente sintetice de sincronizare și audit."},
        {"name": "Demo", "description": "Control local pentru resetarea datelor sintetice."},
    ],
)

_DEFAULT_CORS_ORIGINS = {
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
    "http://localhost:5173",
    "http://localhost:4173",
}
_configured_origins = {
    origin.strip()
    for origin in os.getenv("FARM_REGISTRY_CORS_ORIGINS", "").split(",")
    if origin.strip() and origin.strip() != "*"
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(_configured_origins or _DEFAULT_CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


class GeoJSONPayload(BaseModel):
    type: Literal["Feature", "Polygon", "MultiPolygon"]
    geometry: dict | None = None
    coordinates: list | None = None
    properties: dict = PydanticField(default_factory=dict)


class ValidationResult(BaseModel):
    valid: bool
    area_m2: float | None = None
    issues: list[str] = PydanticField(default_factory=list)


class Parcel(BaseModel):
    """Contract păstrat pentru clientul Farm Registry Web existent."""

    id: str
    farmer: str
    area: float
    status: Literal["Valid", "Review", "Blocked"]
    crop: str
    center: tuple[float, float]


class Farm(BaseModel):
    id: str
    name: str
    owner_name: str
    region: str
    status: str
    area_ha: float


class Field(BaseModel):
    id: str
    farm_id: str
    name: str
    area_ha: float
    status: Literal["Valid", "Review", "Blocked"]
    crop: str
    center: tuple[float, float]


class FarmDetail(Farm):
    fields: list[Field]


TaskStatus = Literal["Planned", "In progress", "Done", "Cancelled"]
TaskPriority = Literal["Low", "Normal", "High"]


class Task(BaseModel):
    id: str
    farm_id: str
    field_id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    due_date: str | None = None
    created_at: str
    updated_at: str


class TaskCreate(BaseModel):
    farm_id: str = PydanticField(min_length=1)
    field_id: str = PydanticField(min_length=1)
    title: str = PydanticField(min_length=1, max_length=200)
    description: str = PydanticField(default="", max_length=2000)
    status: TaskStatus = "Planned"
    priority: TaskPriority = "Normal"
    due_date: str | None = None
    client_action_id: str | None = PydanticField(default=None, max_length=120)


ObservationStatus = Literal["Pending", "Reviewed", "Flagged"]


class Observation(BaseModel):
    id: str
    field_id: str
    status: ObservationStatus
    note: str
    observed_at: str
    client_action_id: str
    created_at: str


class ObservationCreate(BaseModel):
    field_id: str = PydanticField(min_length=1)
    status: ObservationStatus = "Pending"
    note: str = PydanticField(min_length=1, max_length=2000)
    observed_at: str | None = None
    client_action_id: str = PydanticField(min_length=1, max_length=120)


class SyncEvent(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    action: str
    occurred_at: str
    client_action_id: str | None = None


class DemoResetResponse(BaseModel):
    status: Literal["reset"]
    counts: dict[str, int]


def _farm_response(row: dict) -> Farm:
    return Farm(**row)


def _field_response(row: dict) -> Field:
    row = dict(row)
    row["center"] = (row.pop("center_lat"), row.pop("center_lon"))
    return Field(**row)


def _task_response(row: dict) -> Task:
    return Task(**row)


def _observation_response(row: dict) -> Observation:
    return Observation(**row)


@app.get("/health", tags=["Sănătate"], summary="Verifică sănătatea serviciului")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "farm-registry-data-tools"}


@app.get(
    "/parcels",
    response_model=list[Parcel],
    tags=["Registru"],
    summary="Listează parcelele pentru clientul Web legacy",
)
def parcels() -> list[Parcel]:
    result: list[Parcel] = []
    for field in demo_repository.fields():
        farm = demo_repository.farm(field["farm_id"])
        result.append(
            Parcel(
                id=field["id"],
                farmer=farm["owner_name"] if farm else "Fermier Sintetic Necunoscut",
                area=field["area_ha"],
                status=field["status"],
                crop=field["crop"],
                center=(field["center_lat"], field["center_lon"]),
            )
        )
    return result


@app.get(
    "/farms", response_model=list[Farm], tags=["Registru"], summary="Listează fermele sintetice"
)
def farms() -> list[Farm]:
    return [_farm_response(row) for row in demo_repository.farms()]


@app.get(
    "/farms/{farm_id}",
    response_model=FarmDetail,
    tags=["Registru"],
    summary="Afișează o fermă și câmpurile sale",
)
def farm_detail(farm_id: str) -> FarmDetail:
    row = demo_repository.farm(farm_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ferma sintetică nu există")
    fields = [_field_response(field) for field in row.pop("fields", [])]
    return FarmDetail(**row, fields=fields)


@app.get(
    "/fields",
    response_model=list[Field],
    tags=["Registru"],
    summary="Listează câmpurile cu filtre",
)
def fields(
    farm_id: str | None = Query(default=None, description="ID fermă, de forma SYN-FARM-001"),
    status: str | None = Query(default=None, description="Valid, Review sau Blocked"),
    crop: str | None = Query(default=None, description="Cultura, de exemplu Grâu"),
) -> list[Field]:
    return [
        _field_response(row)
        for row in demo_repository.fields(farm_id=farm_id, status=status, crop=crop)
    ]


@app.get(
    "/fields/{field_id}",
    response_model=Field,
    tags=["Registru"],
    summary="Afișează un câmp sintetic",
)
def field_detail(field_id: str) -> Field:
    row = demo_repository.field(field_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Câmpul sintetic nu există")
    return _field_response(row)


@app.get(
    "/tasks",
    response_model=list[Task],
    tags=["Activitate"],
    summary="Listează sarcinile cu filtre",
)
def tasks(
    status: str | None = Query(
        default=None, description="Planned, In progress, Done sau Cancelled"
    ),
    farm_id: str | None = Query(default=None),
    field_id: str | None = Query(default=None),
) -> list[Task]:
    return [
        _task_response(row)
        for row in demo_repository.tasks(status=status, farm_id=farm_id, field_id=field_id)
    ]


@app.post(
    "/tasks",
    response_model=Task,
    status_code=201,
    tags=["Activitate"],
    summary="Creează o sarcină sintetică",
)
def create_task(payload: TaskCreate) -> Task:
    farm = demo_repository.farm(payload.farm_id)
    field = demo_repository.field(payload.field_id)
    if farm is None:
        raise HTTPException(status_code=404, detail="Ferma sintetică nu există")
    if field is None:
        raise HTTPException(status_code=404, detail="Câmpul sintetic nu există")
    if field["farm_id"] != farm["id"]:
        raise HTTPException(status_code=422, detail="Câmpul nu aparține fermei indicate")
    return _task_response(demo_repository.create_task(payload.model_dump()))


@app.get(
    "/observations",
    response_model=list[Observation],
    tags=["Activitate"],
    summary="Listează observațiile cu filtre",
)
def observations(
    field_id: str | None = Query(default=None),
    status: str | None = Query(default=None, description="Pending, Reviewed sau Flagged"),
) -> list[Observation]:
    return [
        _observation_response(row)
        for row in demo_repository.observations(field_id=field_id, status=status)
    ]


@app.post(
    "/observations",
    response_model=Observation,
    status_code=201,
    tags=["Activitate"],
    summary="Creează sau reia idempotent o observație",
)
def create_observation(payload: ObservationCreate) -> Observation:
    if demo_repository.field(payload.field_id) is None:
        raise HTTPException(status_code=404, detail="Câmpul sintetic nu există")
    row, _already_exists = demo_repository.create_observation(payload.model_dump())
    return _observation_response(row)


@app.get(
    "/sync/events",
    response_model=list[SyncEvent],
    tags=["Sincronizare"],
    summary="Listează evenimentele sintetice de sincronizare",
)
def sync_events() -> list[SyncEvent]:
    return [SyncEvent(**row) for row in demo_repository.events()]


@app.post(
    "/demo/reset",
    response_model=DemoResetResponse,
    tags=["Demo"],
    summary="Resetează baza SQLite la fixture-urile deterministe",
)
def reset_demo() -> DemoResetResponse:
    return DemoResetResponse(status="reset", counts=reset_demo_data())


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


@app.post(
    "/validate/parcel",
    response_model=ValidationResult,
    tags=["Registru"],
    summary="Validează geometria GeoJSON a unei parcele",
)
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
