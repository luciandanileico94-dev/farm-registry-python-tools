from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field
from shapely.geometry import shape

app = FastAPI(title="Farm Registry Data Tools", version="1.0.0")

class GeoJSONPayload(BaseModel):
    type: Literal["Feature", "Polygon", "MultiPolygon"]
    geometry: dict | None = None
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
        Parcel(id="MD-CT-00142", farmer="AgroNord SRL", area=42.8, status="Valid", crop="Grâu", center=(47.02, 28.84)),
        Parcel(id="MD-CT-00143", farmer="Ion Balan", area=18.3, status="Review", crop="Porumb", center=(47.04, 28.88)),
        Parcel(id="MD-CT-00144", farmer="Eco Valea Mare", area=64.1, status="Valid", crop="Floarea-soarelui", center=(46.98, 28.92)),
    ]

@app.post("/validate/parcel", response_model=ValidationResult)
def validate_parcel(payload: GeoJSONPayload) -> ValidationResult:
    issues: list[str] = []
    geometry = payload.geometry if payload.type == "Feature" else {"type": payload.type, "coordinates": payload.properties.get("coordinates")}
    if not geometry or "coordinates" not in geometry:
        return ValidationResult(valid=False, issues=["geometry.coordinates is required"])
    try:
        polygon = shape(geometry)
    except (TypeError, ValueError):
        return ValidationResult(valid=False, issues=["invalid GeoJSON geometry"])
    if polygon.is_empty:
        issues.append("geometry is empty")
    if not polygon.is_valid:
        issues.append("geometry has a topology issue")
    if polygon.area <= 0:
        issues.append("area must be greater than zero")
    return ValidationResult(valid=not issues, area_m2=round(polygon.area, 4), issues=issues)
