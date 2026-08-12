# Farm Registry Python Tools

Un backend FastAPI local și testabil pentru un registru agricol demonstrativ.
API-ul este stratul de date comun pentru Farm Registry Web și Farm Registry
Mobile: Web poate lista și valida parcele, iar Mobile poate crea observații și
urmări sarcini. Ambele folosesc aceeași bază SQLite demo și aceleași modele.

## Limită sintetică

Acest proiect conține numai fixture-uri inventate, cu identificatori `SYN-`:
6 ferme, 12 câmpuri/parcele, 12 sarcini, 10 observații și evenimente de
sincronizare/audit. Numele, suprafețele și coordonatele sunt date de test; nu
sunt GPS real, identificatori cadastrali, date despre clienți sau date dintr-un
registru guvernamental. Nu există autentificare, integrări externe ori
pretenția că API-ul este public sau deployed.

Repository-ul folosește SQLite în memorie și însămânțează aceleași date la
import. `POST /demo/reset` golește baza și reîncarcă fixture-urile determinist.
Prin urmare, rularea locală nu creează o bază de producție și nu cere secrete.

## Rulare locală

Este necesar Python 3.11 sau mai nou.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

API-ul este disponibil la `http://127.0.0.1:8000`; documentația OpenAPI este la
`/docs`, cu tag-uri și descrieri în limba română. Pentru clientul Vite, CORS
permite implicit originile exacte `http://localhost:5173`,
`http://127.0.0.1:5173`, `http://localhost:4173` și
`http://127.0.0.1:4173`. În alt mediu, setează
`FARM_REGISTRY_CORS_ORIGINS` ca listă separată prin virgulă, de exemplu
`https://web.example.test,https://preview.example.test`. Lista este explicită,
nu folosește wildcard și credentials sunt dezactivate.

## Endpoint-uri

- `GET /health` — starea serviciului.
- `GET /parcels` — contractul pentru Web: `id`, `farmer`, `area`, `status`,
  `crop`, `center` și un contur GeoJSON `geometry` valid.
- `POST /validate/parcel` — validează GeoJSON `Polygon`/`MultiPolygon`, cu aria geodezică WGS84.
- `GET /farms` și `GET /farms/{farm_id}` — ferme și câmpurile unei ferme.
- `GET /fields` — filtre opționale `farm_id`, `status`, `crop`.
- `GET /fields/{field_id}` — detaliul unui câmp.
- `GET /tasks` — filtre opționale `status`, `farm_id`, `field_id`.
- `POST /tasks` — creează o sarcină; ID-urile fermei și câmpului sunt verificate.
- `GET /observations` — filtre opționale `field_id`, `status`.
- `POST /observations` — creează o observație și este idempotent pentru același `client_action_id`.
- `GET /sync/events` — evenimente sintetice pentru sincronizare/audit.
- `POST /demo/reset` — reîncarcă fixture-urile și întoarce numărătorile.

Toate resursele create de API primesc ID-uri `SYN-`; erorile pentru ID-uri
necunoscute sunt răspunsuri controlate `404`, iar cererile cu schema invalidă
primesc `422`. Contractul de geometrie acceptă numai poziții 2D
`[longitude, latitude]`; structurile GeoJSON malformate întorc `valid: false`,
nu eroare 500.

Geometria fiecărei parcele din `GET /parcels` este un `Polygon` fix și valid,
generat determinist din coordonatele sintetice ale câmpului. Conturul folosește
ordinea GeoJSON `[longitude, latitude]`, este centrat pe valoarea `center`
(`[latitude, longitude]`) și poate fi afișat direct de clientul Web.

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

`area_m2` este calculată geodezic pe elipsoidul WGS84, nu din grade pătrate.
Găurile sunt scăzute, iar componentele unui `MultiPolygon` sunt însumate.
Validarea topologică nu repară geometria; pentru geometrii complexe ori alte
sisteme de coordonate sunt necesare verificări GIS dedicate.

## Testare și verificare

```bash
ruff check .
pytest -q
```

Testele acoperă numărătorile fixture-urilor, filtrele, crearea de sarcini,
idempotency pentru observații, resetarea, ID-uri invalide, forma contractului
Web și validarea geometriei existente. Capturile OpenAPI din `docs/screenshots`
sunt referințe locale; nu indică un URL live.

## Așteptări pentru Render

Repository-ul include un blueprint Render minimal în `render.yaml`. Pentru a
folosi configurația, proprietarul repository-ului trebuie să-l lege de Render
și să execute comanda blueprint din dashboard Render (New → Blueprint), alegând
repository-ul și confirmând serviciul `farm-registry-api-demo`. Render va
interpreta fișierul și va crea așteptatul serviciu web Python gratuit, cu
`pip install .`, Uvicorn și verificarea de sănătate `/health`.

Legarea repository-ului în Render și confirmarea blueprint-ului trebuie făcute
de proprietar; acest repository nu poate face acești pași în locul lui. Nu
pretindem că serviciul este deployed, nu includem un URL real și nu adăugăm
secrete. Valoarea `FARM_REGISTRY_CORS_ORIGINS` trebuie introdusă în Render
proprietarului (câmpul este sincronizat manual), iar `PYTHON_VERSION` este
`3.12`. Datele SQLite în memorie se resetează la repornirea procesului, ceea ce
este potrivit pentru demo, nu pentru persistență de producție.

## Arhitectură

`app/repository.py` definește schema SQLite, fixture-urile și operațiile pentru
ferme, câmpuri, sarcini, observații și evenimente. `app/main.py` definește
modelele Pydantic, routing-ul FastAPI, CORS-ul explicit și validarea GeoJSON.
Nu există integrare MPass, MConnect, cadastru sau alt API extern.
