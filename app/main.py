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

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "farm-registry-data-tools"}

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
