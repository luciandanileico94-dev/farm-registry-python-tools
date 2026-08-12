# Farm Registry Python Tools

Backend FastAPI pentru un registru agricol demonstrativ. Expune date sintetice
despre ferme, câmpuri/parcele, sarcini, observații și evenimente de
sincronizare, plus validare GeoJSON, reset determinist și documentație OpenAPI.

Acesta este un API de portofoliu, nu un registru agricol real. Clientul Web are
calea de citire configurată către API; interfața Mobile folosește în prezent
fixture-uri locale și un flux offline.

## API live

Demo-ul public este găzduit pe Render:

- [API](https://farm-registry-api-demo.onrender.com)
- [Health check](https://farm-registry-api-demo.onrender.com/health)
- [Documentație interactivă OpenAPI](https://farm-registry-api-demo.onrender.com/docs)

Instanța live este numai pentru demonstrație. Datele create sau resetate pot
dispărea la restart, redeploy ori înlocuirea procesului.

## Endpoint-uri

- `GET /health` — verifică starea serviciului.
- `GET /parcels` — listează contractul pentru Web: identificare, fermier,
  suprafață, stare, cultură, centru și contur GeoJSON.
- `GET /farms` — listează fermele sintetice.
- `GET /farms/{farm_id}` — întoarce o fermă și câmpurile sale.
- `GET /fields` — listează câmpurile; acceptă filtrele `farm_id`, `status` și
  `crop`.
- `GET /fields/{field_id}` — întoarce un câmp.
- `GET /tasks` — listează sarcinile; acceptă filtrele `status`, `farm_id` și
  `field_id`.
- `POST /tasks` — creează o sarcină după verificarea fermei, câmpului și a
  relației dintre ele.
- `GET /observations` — listează observațiile; acceptă filtrele `field_id` și
  `status`.
- `POST /observations` — creează o observație; repetarea aceluiași
  `client_action_id` întoarce observația existentă.
- `GET /sync/events` — listează evenimentele sintetice de sincronizare/audit.
- `POST /validate/parcel` — validează un `Polygon` sau `MultiPolygon` GeoJSON și
  calculează aria geodezică WGS84 în metri pătrați.
- `POST /demo/reset` — golește baza procesului curent și reîncarcă fixture-urile
  deterministe.

FastAPI publică interfața Swagger UI la `GET /docs` și schema OpenAPI la
`GET /openapi.json`. Cererile cu resurse necunoscute primesc răspunsuri `404`,
iar payload-urile care nu respectă modelele primesc `422`.

## Dezvoltare locală

Este necesar Python 3.11 sau mai nou.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

API-ul pornește la [http://127.0.0.1:8000](http://127.0.0.1:8000), iar
documentația la [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Pentru verificare:

```bash
ruff check .
pytest -q
```

CORS permite implicit originile locale Vite de pe porturile `5173` și `4173`,
pentru `localhost` și `127.0.0.1`. Pentru alte medii, setează
`FARM_REGISTRY_CORS_ORIGINS` la o listă de origini exacte, separate prin
virgulă; wildcard-ul nu este acceptat.

## Deploy pe Render

Fișierul `render.yaml` conține un Render Blueprint pentru serviciul web Python
`farm-registry-api-demo`. Configurația instalează pachetul cu `pip install .`,
pornește Uvicorn pe portul oferit de Render și folosește `/health` drept health
check.

Pentru un deploy propriu, conectează repository-ul în Render, creează serviciul
din Blueprint și configurează manual `FARM_REGISTRY_CORS_ORIGINS` cu originile
clienților permiși. Blueprint-ul fixează `PYTHON_VERSION` la `3.12`.

## Limita datelor sintetice

Toate datele demo sunt inventate și identificabile prin prefixul `SYN-`.
Seed-ul inițial conține 6 ferme, 12 câmpuri, 12 sarcini, 10 observații și
evenimente de sincronizare. Nu sunt date cadastrale, GPS reale sau date despre
clienți.

Repository-ul folosește SQLite exclusiv în memorie. Fiecare proces are propria
bază, seed-uită la pornire; scrierile nu supraviețuiesc restartului și nu sunt
partajate sigur între mai multe procese. `POST /demo/reset` restaurează doar
starea sintetică a procesului care deservește cererea. Această arhitectură este
potrivită pentru demo și teste, nu pentru o bază persistentă de producție sau
sincronizare durabilă.

API-ul nu include autentificare, autorizare, integrare cu registre/cadastru,
integrare MPass/MConnect ori alte integrări reale. Pentru producție ar fi
necesare separat persistență, securitate, migrații, observabilitate și un model
de sincronizare durabil.

## Repository-uri conexe

- [Farm Registry Web](https://github.com/luciandanileico94-dev/farm-registry-web)
  · [demo live](https://farm-registry-web.vercel.app) — calea de citire este
  configurată către acest API.
- [Farm Registry Mobile](https://github.com/luciandanileico94-dev/farm-registry-mobile)
  · [demo live](https://farm-registry-mobile.vercel.app) — interfața folosește
  fixture-uri locale și flux offline; nu scrie în backend-ul live.
