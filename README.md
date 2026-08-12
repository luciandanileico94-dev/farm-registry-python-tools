# Farm Registry Python Tools

Un demo Python verificabil pentru portofoliu: un API FastAPI care validează geometrii GeoJSON și expune date sintetice pentru un client web. Proiectul nu se conectează la MPass, MConnect sau la registre guvernamentale și nu conține date reale de cadastru ori date de client.

## Rulare locală

Este necesar Python 3.11 sau mai nou.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

API-ul este disponibil la `http://127.0.0.1:8000`, iar documentația OpenAPI la `/docs`.

## API

- `GET /health` — verificare simplă a serviciului.
- `GET /parcels` — listă de parcele demo, cu schema păstrată pentru clientul Farm Registry Web.
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

`area_m2` este calculată geodezic pe elipsoidul WGS84, nu din grade pătrate. Pentru date globale, aproximări grosiere, geometrii foarte complexe sau sisteme de coordonate diferite de lon/lat WGS84 sunt necesare verificări și proiecții GIS dedicate. Sunt acceptate doar Polygon și MultiPolygon; coordonatele trebuie să fie lon/lat valide, iar validarea topologică nu repară geometria.

## Testare și CI

```bash
ruff check .
pytest -q
```

Workflow-ul GitHub Actions instalează proiectul cu extra-urile de dezvoltare și rulează Ruff și pytest la push și pull request. Acest README descrie configurația, nu afirmă că fiecare rulare externă este verde.

## Notă despre trimitere

Hardening-ul de după trimitere păstrează istoricul și tag-ul imuabil `submission-21663739-2026-08-12`; tag-ul nu este modificat. Schimbările sunt limitate la corectitudinea ariei, validarea inputului, documentație, teste și verificările CI.

Interfață asociată: [Farm Registry Web](https://github.com/luciandanileico94-dev/farm-registry-web).
