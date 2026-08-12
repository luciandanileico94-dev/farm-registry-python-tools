# Farm Registry Python Tools

Небольшой проверяемый Python‑проект для портфолио к закупке MAIA. Он показывает FastAPI, Pydantic, Shapely, обработку GeoJSON, тесты и CI. Это synthetic demo: он не подключается к MPass/MConnect и не использует реальные кадастровые данные.

## API

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

- `GET /health`
- `GET /parcels` — typed demo endpoint consumed by the React web client.
- `POST /validate/parcel` — принимает GeoJSON Feature и возвращает `valid`, площадь и список topology issues.
- OpenAPI: `http://127.0.0.1:8000/docs`

## Что доказывает для тендера

| Требование | Доказательство |
|---|---|
| Python scripts/services | `app/main.py` |
| GeoJSON / spatial validation | Shapely `shape`, validity and area checks |
| REST API / OpenAPI | FastAPI endpoints and `/docs` |
| Tests / CI | `tests/test_main.py`, GitHub Actions |

Связанный интерфейс: [Farm Registry Web](https://github.com/luciandanileico94-dev/farm-registry-web).
