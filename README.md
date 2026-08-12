# Farm Registry Python Tools

Un demo Python verificabil pentru portofoliu: un API FastAPI care validează geometrii GeoJSON și expune date sintetice pentru un client web. Proiectul nu se conectează la MPass, MConnect sau la registre guvernamentale și nu conține date reale de cadastru ori date de client.

## Stack exact

- Python `>=3.11`.
- FastAPI `>=0.115,<1` și Uvicorn `>=0.32,<1` pentru API și server local.
- Pydantic `>=2.9,<3` pentru modelele de request și response.
- Shapely `>=2.0,<3` pentru geometrie și validare topologică.
- pyproj `>=3.6,<4` pentru aria geodezică WGS84.
- pytest `>=8.3,<9`, httpx `>=0.27,<1` și Ruff `>=0.7,<1` pentru testare și linting.

Versiunile și limitele de compatibilitate sunt declarate în `pyproject.toml`.

## Rulare locală

Este necesar Python 3.11 sau mai nou.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

API-ul este disponibil la `http://127.0.0.1:8000`, iar documentația OpenAPI la `/docs`.

Pentru clientul Vite, CORS permite implicit originile exacte `http://localhost:5173`,
`http://127.0.0.1:5173`, `http://localhost:4173` și `http://127.0.0.1:4173`.
În alte medii, setează `FARM_REGISTRY_CORS_ORIGINS` ca listă separată prin virgulă,
de exemplu `https://web.example.test,https://preview.example.test`. Nu se folosesc
wildcard-uri sau credentials.

## Capturi reale ale API-ului

Capturile sunt din documentația OpenAPI generată automat pentru API-ul curent, accesibilă local la `/docs` după pornirea serverului. Nu este un backend public deployed și nu există un live URL:

- [Desktop](docs/screenshots/openapi-desktop.png)
- [Mobil](docs/screenshots/openapi-mobile.png)

## API

- `GET /health` — verificare simplă a serviciului.
- `GET /parcels` — listă de parcele demo, cu schema păstrată pentru clientul Farm Registry Web;
  fiecare parcelă include `geometry`, un GeoJSON `Polygon` fix și valid, în coordonate
  `[longitude, latitude]`, consistent cu `center` (`[latitude, longitude]`). Clientul web
  poate afișa astfel conturul primit de la API, fără să-l sintetizeze din centru.
- `POST /validate/parcel` — primește un GeoJSON `Feature` cu geometrie `Polygon`/`MultiPolygon` sau un GeoJSON direct și întoarce `valid`, `area_m2` și problemele de topologie.

Exemplu de corp pentru validare:

```json
{
  "type": "Feature",
  "properties": {},
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[28, 47], [28.001, 47], [28.001, 47.001], [28, 47.001], [28, 47]]]
  }
}
```

`area_m2` este calculată geodezic pe elipsoidul WGS84, nu din grade pătrate. Contractul
acceptă numai `Polygon` și `MultiPolygon` cu poziții strict 2D `[longitude, latitude]`:
altitudinea RFC opțională (a treia valoare) este respinsă ca geometrie invalidă.
Structurile GeoJSON lipsă sau malformate întorc `valid: false`, nu eroare 500.
Pentru date globale, aproximări grosiere, geometrii foarte complexe sau sisteme de
coordonate diferite de lon/lat WGS84 sunt necesare verificări și proiecții GIS dedicate.
Validarea topologică nu repară geometria.

## Arhitectură și flux de date

`app/main.py` definește aplicația, modelele Pydantic și cele trei endpoint-uri. Pentru `/validate/parcel`, requestul este modelat ca `GeoJSONPayload`, geometria este extrasă din Feature sau din GeoJSON direct, coordonatele sunt verificate ca lon/lat finite, apoi Shapely construiește și verifică Polygon/MultiPolygon. Pentru geometriile acceptate, pyproj calculează aria WGS84: aria găurilor este scăzută, iar ariile componentelor unui MultiPolygon sunt adunate. Response-ul este `ValidationResult`.

`GET /parcels` construiește în memorie trei obiecte `Parcel` cu identificatori `SYN-`, nume
`Demo`/`Exemplu` și contururi GeoJSON fixe; geometria este verificată ca Polygon valid și
nevid prin Shapely. Nu există citire dintr-o bază de date în acest serviciu. Schema
response-ului este verificată de FastAPI prin `response_model=list[Parcel]`.

## Dovezi criteriu → fișier/test

| Criteriu | Implementare | Dovadă automată |
| --- | --- | --- |
| Configurație Ruff modernă | `pyproject.toml`, `[tool.ruff.lint]` | `ruff check .` |
| Contractul `/parcels` | `app/main.py`, `Parcel`, `response_model` | `test_get_parcels_keeps_web_client_contract` |
| Identificatori și nume sintetice | `app/main.py`, valorile `SYN-`, `Demo`, `Exemplu` | aceeași probă pentru `/parcels` |
| Limite lon/lat și valori finite | `_validate_coordinate_ranges` | `test_rejects_coordinates_outside_lon_lat_ranges`, `test_rejects_non_finite_coordinates` |
| Găuri și MultiPolygon | `_polygon_area_m2`, `_geodesic_area_m2` | `test_subtracts_polygon_holes_from_geodesic_area`, `test_sums_multipolygon_parts` |
| CI reproducibil | `.github/workflows/ci.yml` | pașii `ruff check .` și `pytest -q` |

## Testare și CI

```bash
ruff check .
pytest -q
```

Workflow-ul GitHub Actions din `.github/workflows/ci.yml` instalează proiectul cu extra-urile de dezvoltare și rulează Ruff și pytest la push și pull request.

Interfață asociată: [Farm Registry Web](https://github.com/luciandanileico94-dev/farm-registry-web).

## Notă post-submission — audit fixes

Tag: `final-audit-fixes` (12 august 2026). Această notă documentează corecțiile
finale pentru CORS și limita strictă 2D GeoJSON. Nu afirmă că un CI de submission
a fost verde sau reproductibil și nu afirmă efectuarea unui security audit de
dependențe.
