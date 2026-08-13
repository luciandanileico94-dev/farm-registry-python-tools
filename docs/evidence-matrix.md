# Matrice de evidence verificabilă

Matricea leagă fiecare afirmație de implementarea auditată și de o comandă care poate
fi rulată din rădăcina repository-ului. Comenzile `pytest` indică numai teste care există
în arborele curent; ele nu pretind că teste inexistente sau servicii externe sunt evidence.

## Endpoint-uri și limite runtime

| Method | Path | Evidence path/symbol | Verification command | Boundary |
| --- | --- | --- | --- | --- |
| `GET` | `/health` | [`app/main.py`](../app/main.py): `health` | `pytest -q tests/test_main.py::test_health` | Semnal de proces; nu verifică persistența sau dependențe externe. |
| `GET` | `/parcels` | [`app/main.py`](../app/main.py): `parcels`, `_parcel_geometry`, `Parcel` | `pytest -q tests/test_main.py::test_get_parcels_keeps_web_client_contract tests/test_main.py::test_parcel_geometry_is_deterministic_and_matches_center` | Contract legacy derivat din câmpurile sintetice; geometria este un contur demo. |
| `GET` | `/farms` | [`app/main.py`](../app/main.py): `farms`; [`app/repository.py`](../app/repository.py): `DemoRepository.farms` | `pytest -q tests/test_registry.py::test_seed_counts_and_synthetic_ids` | Numai date `SYN-` din memoria procesului. |
| `GET` | `/farms/{farm_id}` | [`app/main.py`](../app/main.py): `farm_detail`; [`app/repository.py`](../app/repository.py): `DemoRepository.farm` | `pytest -q tests/test_registry.py::test_farm_detail_contains_its_fields tests/test_registry.py::test_invalid_ids_are_safe_404s` | Detaliu sintetic; ID necunoscut produce `404`. |
| `GET` | `/fields` | [`app/main.py`](../app/main.py): `fields`; [`app/repository.py`](../app/repository.py): `DemoRepository.fields` | `pytest -q tests/test_registry.py::test_field_and_task_filters` | Filtre exacte pe `farm_id`, `status`, `crop`; fără interogare cadastrală. |
| `GET` | `/fields/{field_id}` | [`app/main.py`](../app/main.py): `field_detail`; [`app/repository.py`](../app/repository.py): `DemoRepository.field` | `pytest -q tests/test_registry.py::test_invalid_ids_are_safe_404s` | Testul existent verifică ramura `404`; datele sunt exclusiv sintetice. |
| `GET` | `/tasks` | [`app/main.py`](../app/main.py): `tasks`; [`app/repository.py`](../app/repository.py): `DemoRepository.tasks` | `pytest -q tests/test_registry.py::test_field_and_task_filters` | Listă volatilă, filtrată în SQLite-ul procesului. |
| `POST` | `/tasks` | [`app/main.py`](../app/main.py): `TaskCreate`, `create_task`; [`app/repository.py`](../app/repository.py): `DemoRepository.create_task` | `pytest -q tests/test_registry.py::test_create_task_validates_relationship_and_returns_shape` | Verifică existența și relația farmă–câmp; scrierea nu supraviețuiește restartului. |
| `GET` | `/observations` | [`app/main.py`](../app/main.py): `observations`; [`app/repository.py`](../app/repository.py): `DemoRepository.observations` | `pytest -q tests/test_registry.py::test_field_and_task_filters` | Filtre exacte pe `field_id` și `status`; date volatile. |
| `POST` | `/observations` | [`app/main.py`](../app/main.py): `ObservationCreate`, `create_observation`; [`app/repository.py`](../app/repository.py): `DemoRepository.create_observation` | `pytest -q tests/test_registry.py::test_observation_is_idempotent_by_client_action_id` | Idempotent numai după `client_action_id` în baza procesului; fără sincronizare durabilă. |
| `GET` | `/sync/events` | [`app/main.py`](../app/main.py): `sync_events`; [`app/repository.py`](../app/repository.py): `DemoRepository.events` | `pytest -q tests/test_registry.py::test_seed_counts_and_synthetic_ids` | Jurnal sintetic în memorie, nu event store sau audit durabil. |
| `POST` | `/validate/parcel` | [`app/main.py`](../app/main.py): `GeoJSONPayload`, `validate_parcel`, `_geometry_from_payload`, `_geodesic_area_m2` | `pytest -q tests/test_main.py -k 'geojson or polygon or multipolygon or coordinate'` | Validare locală `Polygon`/`MultiPolygon`; aria este geodezică WGS84, fără cadastru/GPS real. |
| `POST` | `/demo/reset` | [`app/main.py`](../app/main.py): `reset_demo`; [`app/repository.py`](../app/repository.py): `reset_demo_data`, `DemoRepository.reset` | `pytest -q tests/test_registry.py::test_reset_restores_deterministic_counts` | Resetează numai procesul curent și elimină scrierile demo din acel proces. |
| `OPTIONS` | `*` (CORS preflight) | [`app/main.py`](../app/main.py): `_DEFAULT_CORS_ORIGINS`, `_configured_origins`, `CORSMiddleware` | `pytest -q tests/test_main.py -k cors` | Origini explicite și metode `GET`, `POST`, `OPTIONS`; wildcard-ul configurat este ignorat. |
| `Runtime` | `DemoRepository` | [`app/repository.py`](../app/repository.py): `DemoRepository.__init__`, `sqlite3.connect(":memory:")`, `Lock` | `pytest -q tests/test_registry.py` | SQLite per proces și lock in-process; fără persistență sau coordonare multi-proces. |
| `Runtime` | `seed/reset` | [`app/repository.py`](../app/repository.py): `DemoRepository.reset`, `_seed_farms`, `_seed_fields`, `_seed_tasks`, `_seed_observations`, `_seed_events` | `pytest -q tests/test_registry.py::test_seed_counts_and_synthetic_ids tests/test_registry.py::test_reset_restores_deterministic_counts` | Fixture-uri deterministe, exclusiv sintetice. |
| `Runtime` | `GeoJSON` | [`app/main.py`](../app/main.py): `GEOD`, `_validate_coordinate_ranges`, `_polygon_area_m2`, `_geodesic_area_m2` | `pytest -q tests/test_main.py -k 'geojson or polygon or multipolygon or coordinate'` | Implementarea este în `app/main.py`; `app/geo.py` nu există în versiunea auditată, deci nu poate fi evidence path. |
| `Deploy` | `render.yaml` | [`render.yaml`](../render.yaml): `farm-registry-api-demo`, `startCommand`, `healthCheckPath`, `PYTHON_VERSION` | `python -c 'from pathlib import Path; s=Path("render.yaml").read_text(); assert all(x in s for x in ("farm-registry-api-demo", "uvicorn app.main:app", "healthCheckPath: /health", "value: \"3.12\""))'` | Render pornește demo-ul public; configurația nu adaugă persistență, auth sau integrări reale. |

## Căi de verificare la nivel de repository

Comenzile documentate de proiect și executate de CI sunt:

```bash
ruff check .
pytest -q
```

Configurația lor este în [`pyproject.toml`](../pyproject.toml), iar jobul care le rulează
este în [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). Nu există în arborele
auditat fișierele `tests/test_api.py` sau `tests/test_repository.py`; căile reale folosite
mai sus sunt [`tests/test_main.py`](../tests/test_main.py) și
[`tests/test_registry.py`](../tests/test_registry.py).

## Ce nu dovedește această matrice

Evidence-ul confirmă comportamentul demo local și configurația declarativă. Nu
dovedește disponibilitatea continuă a URL-ului live, persistență de producție,
autentificare/autorizare, date cadastrale sau GPS reale și nici integrări MPass ori
MConnect.
