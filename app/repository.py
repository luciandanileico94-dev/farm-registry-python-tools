"""Repository SQLite pentru datele demo, strict sintetice.

Repository-ul folosește o bază SQLite în memorie. Astfel, aplicația poate fi
rulată local fără fișiere de date, credențiale sau conexiuni către sisteme
externe, iar resetarea demo-ului este repetabilă.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from threading import Lock
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class DemoRepository:
    """Repository thread-safe pentru baza SQLite sintetică a aplicației."""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = Lock()
        self._create_schema()
        self.reset()

    def _create_schema(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE farms (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    region TEXT NOT NULL,
                    status TEXT NOT NULL,
                    area_ha REAL NOT NULL
                );
                CREATE TABLE fields (
                    id TEXT PRIMARY KEY,
                    farm_id TEXT NOT NULL REFERENCES farms(id),
                    name TEXT NOT NULL,
                    area_ha REAL NOT NULL,
                    status TEXT NOT NULL,
                    crop TEXT NOT NULL,
                    center_lat REAL NOT NULL,
                    center_lon REAL NOT NULL
                );
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    farm_id TEXT NOT NULL REFERENCES farms(id),
                    field_id TEXT NOT NULL REFERENCES fields(id),
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    due_date TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE observations (
                    id TEXT PRIMARY KEY,
                    field_id TEXT NOT NULL REFERENCES fields(id),
                    status TEXT NOT NULL,
                    note TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    client_action_id TEXT UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE sync_events (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    client_action_id TEXT
                );
                """
            )

    def reset(self) -> None:
        """Golește și re-seminează baza cu aceleași date de fiecare dată."""
        with self.lock, self.connection:
            for table in ("sync_events", "observations", "tasks", "fields", "farms"):
                self.connection.execute(f"DELETE FROM {table}")
            self._seed_farms()
            self._seed_fields()
            self._seed_tasks()
            self._seed_observations()
            self._seed_events()

    def _seed_farms(self) -> None:
        farms = [
            (
                "SYN-FARM-001", "Ferma Fictivă Albastră", "Fermier Sintetic Ana",
                "Județul Demo Nord", "Active", 61.1,
            ),
            (
                "SYN-FARM-002", "Ferma Exemplu Mărginimea", "Familia Fictivă Pop",
                "Județul Demo Vest", "Active", 85.4,
            ),
            (
                "SYN-FARM-003", "Exploatația Sintetică Verde", "Fermier Fictiv Mihai",
                "Județul Demo Centru", "Review", 73.7,
            ),
            (
                "SYN-FARM-004", "Gospodăria Demo de Câmp", "Asociația Fictivă Lan",
                "Județul Demo Est", "Active", 48.2,
            ),
            (
                "SYN-FARM-005", "Ferma Inventată Floarea", "Fermier Sintetic Ioana",
                "Județul Demo Sud", "Review", 92.6,
            ),
            (
                "SYN-FARM-006", "Terenurile Fictive Armonia", "Cooperativa Demo Armonia",
                "Județul Demo Deal", "Active", 56.8,
            ),
        ]
        self.connection.executemany(
            "INSERT INTO farms (id, name, owner_name, region, status, area_ha) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            farms,
        )

    def _seed_fields(self) -> None:
        fields = [
            ("SYN-FIELD-001", "SYN-FARM-001", "Parcela Fictivă 1A", 42.8,
             "Valid", "Grâu", 47.0200, 28.8400),
            ("SYN-FIELD-002", "SYN-FARM-001", "Parcela Fictivă 1B", 18.3,
             "Review", "Porumb", 47.0400, 28.8800),
            ("SYN-FIELD-003", "SYN-FARM-002", "Parcela Exemplu 2A", 64.1,
             "Valid", "Floarea-soarelui", 46.9800, 28.9200),
            ("SYN-FIELD-004", "SYN-FARM-002", "Parcela Exemplu 2B", 21.3,
             "Blocked", "Rapiță", 46.9900, 28.9000),
            ("SYN-FIELD-005", "SYN-FARM-003", "Câmp Sintetic 3A", 37.6,
             "Review", "Orz", 47.0800, 28.7600),
            ("SYN-FIELD-006", "SYN-FARM-003", "Câmp Sintetic 3B", 36.1,
             "Valid", "Soia", 47.1000, 28.7800),
            ("SYN-FIELD-007", "SYN-FARM-004", "Lot Demo 4A", 12.4,
             "Valid", "Legume", 46.9200, 28.8300),
            ("SYN-FIELD-008", "SYN-FARM-004", "Lot Demo 4B", 35.8,
             "Review", "Lucernă", 46.9400, 28.8500),
            ("SYN-FIELD-009", "SYN-FARM-005", "Teren Fictiv 5A", 52.7,
             "Valid", "Grâu", 47.1600, 28.9600),
            ("SYN-FIELD-010", "SYN-FARM-005", "Teren Fictiv 5B", 39.9,
             "Blocked", "Porumb", 47.1800, 28.9400),
            ("SYN-FIELD-011", "SYN-FARM-006", "Parcelă Armonia 6A", 28.5,
             "Valid", "Rapiță", 47.2200, 28.7000),
            ("SYN-FIELD-012", "SYN-FARM-006", "Parcelă Armonia 6B", 28.3,
             "Review", "Floarea-soarelui", 47.2400, 28.7200),
        ]
        self.connection.executemany(
            """INSERT INTO fields
            (id, farm_id, name, area_ha, status, crop, center_lat, center_lon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            fields,
        )

    def _seed_tasks(self) -> None:
        tasks = [
            (
                "SYN-TASK-001", "SYN-FARM-001", "SYN-FIELD-001",
                "Verifică marginea parcelei", "Confirmă marginea sintetică în aplicația web.",
                "Planned", "High", "2026-08-15",
            ),
            (
                "SYN-TASK-002", "SYN-FARM-001", "SYN-FIELD-002",
                "Notează starea porumbului", "Colectează o notă din terenul demo.",
                "In progress", "Normal", "2026-08-16",
            ),
            (
                "SYN-TASK-003", "SYN-FARM-002", "SYN-FIELD-003",
                "Revizuiește cultura", "Compară observațiile sintetice.",
                "Done", "Low", "2026-08-10",
            ),
            (
                "SYN-TASK-004", "SYN-FARM-002", "SYN-FIELD-004",
                "Clarifică blocarea", "Adaugă motivul de test pentru review.",
                "Planned", "High", "2026-08-17",
            ),
            (
                "SYN-TASK-005", "SYN-FARM-003", "SYN-FIELD-005",
                "Verifică orzul", "Completează checklist-ul demo.",
                "In progress", "Normal", "2026-08-18",
            ),
            (
                "SYN-TASK-006", "SYN-FARM-003", "SYN-FIELD-006",
                "Înregistrează nota de cultură", "Folosește formularul mobil sintetic.",
                "Done", "Normal", "2026-08-11",
            ),
            (
                "SYN-TASK-007", "SYN-FARM-004", "SYN-FIELD-007",
                "Confirmă lotul demo", "Verifică datele de identificare sintetice.",
                "Planned", "Low", "2026-08-19",
            ),
            (
                "SYN-TASK-008", "SYN-FARM-004", "SYN-FIELD-008",
                "Planifică observația", "Pregătește vizita de test.",
                "Cancelled", "Low", "2026-08-12",
            ),
            (
                "SYN-TASK-009", "SYN-FARM-005", "SYN-FIELD-009",
                "Verifică grâul", "Testează fluxul comun Web și Mobile.",
                "Done", "High", "2026-08-09",
            ),
            (
                "SYN-TASK-010", "SYN-FARM-005", "SYN-FIELD-010",
                "Documentează excepția", "Păstrează un caz blocat pentru demonstrație.",
                "In progress", "High", "2026-08-20",
            ),
            (
                "SYN-TASK-011", "SYN-FARM-006", "SYN-FIELD-011",
                "Pregătește recoltarea demo", "Actualizează starea sarcinii.",
                "Planned", "Normal", "2026-08-21",
            ),
            (
                "SYN-TASK-012", "SYN-FARM-006", "SYN-FIELD-012",
                "Revizuiește floarea-soarelui", "Compară două observații sintetice.",
                "Done", "Low", "2026-08-13",
            ),
        ]
        created = "2026-08-12T09:00:00+00:00"
        self.connection.executemany(
            """INSERT INTO tasks
            (
                id, farm_id, field_id, title, description, status, priority, due_date,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [task + (created, created) for task in tasks],
        )

    def _seed_observations(self) -> None:
        observations = [
            (
                "SYN-OBS-001", "SYN-FIELD-001", "Reviewed",
                "Răsărire uniformă în parcela fictivă.",
                "2026-08-01T08:15:00+00:00", "SYN-ACTION-001",
            ),
            (
                "SYN-OBS-002", "SYN-FIELD-002", "Pending",
                "Necesită o nouă verificare vizuală.",
                "2026-08-02T09:20:00+00:00", "SYN-ACTION-002",
            ),
            (
                "SYN-OBS-003", "SYN-FIELD-003", "Reviewed",
                "Cultură sintetică în parametri.",
                "2026-08-03T10:00:00+00:00", "SYN-ACTION-003",
            ),
            (
                "SYN-OBS-004", "SYN-FIELD-004", "Flagged",
                "Geometrie demo marcată pentru review.",
                "2026-08-04T10:40:00+00:00", "SYN-ACTION-004",
            ),
            (
                "SYN-OBS-005", "SYN-FIELD-005", "Pending",
                "Observație de test din fluxul mobil.",
                "2026-08-05T11:30:00+00:00", "SYN-ACTION-005",
            ),
            (
                "SYN-OBS-006", "SYN-FIELD-006", "Reviewed",
                "Frunze uniforme în datele sintetice.",
                "2026-08-06T12:00:00+00:00", "SYN-ACTION-006",
            ),
            (
                "SYN-OBS-007", "SYN-FIELD-007", "Reviewed",
                "Lot mic, fără excepții demo.",
                "2026-08-07T12:20:00+00:00", "SYN-ACTION-007",
            ),
            (
                "SYN-OBS-008", "SYN-FIELD-008", "Flagged",
                "Necesită verificare în aplicația web.",
                "2026-08-08T13:00:00+00:00", "SYN-ACTION-008",
            ),
            (
                "SYN-OBS-009", "SYN-FIELD-009", "Pending",
                "Observație nouă pentru sincronizare.",
                "2026-08-09T13:40:00+00:00", "SYN-ACTION-009",
            ),
            (
                "SYN-OBS-010", "SYN-FIELD-010", "Flagged",
                "Caz blocat păstrat pentru testare.",
                "2026-08-10T14:10:00+00:00", "SYN-ACTION-010",
            ),
        ]
        created = "2026-08-12T09:00:00+00:00"
        self.connection.executemany(
            """INSERT INTO observations
            (id, field_id, status, note, observed_at, client_action_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [observation + (created,) for observation in observations],
        )

    def _seed_events(self) -> None:
        events = []
        for number in range(1, 7):
            events.append(
                (
                    f"SYN-EVENT-{number:03d}", "farm", f"SYN-FARM-{number:03d}",
                    "seeded", f"2026-08-12T08:{number:02d}:00+00:00", None,
                )
            )
        for number in range(1, 7):
            events.append(
                (
                    f"SYN-EVENT-{number + 6:03d}", "field", f"SYN-FIELD-{number:03d}",
                    "seeded", f"2026-08-12T08:{number + 10:02d}:00+00:00", None,
                )
            )
        self.connection.executemany(
            """INSERT INTO sync_events
            (id, entity_type, entity_id, action, occurred_at, client_action_id)
            VALUES (?, ?, ?, ?, ?, ?)""",
            events,
        )

    def _rows(self, query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(row) for row in self.connection.execute(query, parameters).fetchall()]

    def _row(self, query: str, parameters: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self._rows(query, parameters)
        return rows[0] if rows else None

    def farms(self) -> list[dict[str, Any]]:
        return self._rows(
            "SELECT id, name, owner_name, region, status, area_ha FROM farms ORDER BY id"
        )

    def farm(self, farm_id: str) -> dict[str, Any] | None:
        farm = self._row(
            "SELECT id, name, owner_name, region, status, area_ha FROM farms WHERE id = ?",
            (farm_id,),
        )
        if farm is not None:
            farm["fields"] = self.fields(farm_id=farm_id)
        return farm

    def fields(
        self, farm_id: str | None = None, status: str | None = None, crop: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if farm_id is not None:
            clauses.append("farm_id = ?")
            parameters.append(farm_id)
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status)
        if crop is not None:
            clauses.append("crop = ?")
            parameters.append(crop)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._rows(
            "SELECT id, farm_id, name, area_ha, status, crop, center_lat, center_lon FROM fields"
            + where
            + " ORDER BY id",
            tuple(parameters),
        )

    def field(self, field_id: str) -> dict[str, Any] | None:
        return self._row(
            "SELECT id, farm_id, name, area_ha, status, crop, center_lat, center_lon "
            "FROM fields WHERE id = ?",
            (field_id,),
        )

    def tasks(
        self, status: str | None = None, farm_id: str | None = None, field_id: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for column, value in (("status", status), ("farm_id", farm_id), ("field_id", field_id)):
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._rows(
            "SELECT id, farm_id, field_id, title, description, status, priority, due_date, "
            "created_at, updated_at FROM tasks"
            + where
            + " ORDER BY id",
            tuple(parameters),
        )

    def create_task(self, values: dict[str, Any]) -> dict[str, Any]:
        with self.lock, self.connection:
            next_number = self._next_id_number("tasks", "SYN-TASK-")
            task_id = f"SYN-TASK-{next_number:03d}"
            now = _utc_now()
            row = (
                task_id,
                values["farm_id"],
                values["field_id"],
                values["title"],
                values.get("description", ""),
                values.get("status", "Planned"),
                values.get("priority", "Normal"),
                values.get("due_date"),
                now,
                now,
            )
            self.connection.execute(
                """INSERT INTO tasks
                (
                    id, farm_id, field_id, title, description, status, priority, due_date,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                row,
            )
            self._insert_event(
                task_id, "task", task_id, "created", now, values.get("client_action_id")
            )
            return dict(
                self.connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            )

    def observations(
        self, field_id: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        for column, value in (("field_id", field_id), ("status", status)):
            if value is not None:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return self._rows(
            "SELECT id, field_id, status, note, observed_at, client_action_id, created_at "
            "FROM observations"
            + where
            + " ORDER BY id",
            tuple(parameters),
        )

    def create_observation(self, values: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        with self.lock, self.connection:
            existing_row = self.connection.execute(
                "SELECT id, field_id, status, note, observed_at, client_action_id, created_at "
                "FROM observations WHERE client_action_id = ?",
                (values["client_action_id"],),
            ).fetchone()
            existing = dict(existing_row) if existing_row is not None else None
            if existing is not None:
                return existing, True
            number = self._next_id_number("observations", "SYN-OBS-")
            observation_id = f"SYN-OBS-{number:03d}"
            now = _utc_now()
            row = (
                observation_id,
                values["field_id"],
                values.get("status", "Pending"),
                values["note"],
                values.get("observed_at") or now,
                values["client_action_id"],
                now,
            )
            self.connection.execute(
                """INSERT INTO observations
                (id, field_id, status, note, observed_at, client_action_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                row,
            )
            self._insert_event(
                observation_id, "observation", observation_id, "created", now,
                values["client_action_id"],
            )
            return (
                dict(
                    self.connection.execute(
                        "SELECT * FROM observations WHERE id = ?", (observation_id,)
                    ).fetchone()
                ),
                False,
            )

    def events(self) -> list[dict[str, Any]]:
        return self._rows(
            "SELECT id, entity_type, entity_id, action, occurred_at, client_action_id "
            "FROM sync_events ORDER BY id"
        )

    def _insert_event(
        self,
        event_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        occurred_at: str,
        client_action_id: str | None,
    ) -> None:
        number = self._next_id_number("sync_events", "SYN-EVENT-")
        self.connection.execute(
            "INSERT INTO sync_events "
            "(id, entity_type, entity_id, action, occurred_at, client_action_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                f"SYN-EVENT-{number:03d}", entity_type, entity_id, action,
                occurred_at, client_action_id,
            ),
        )

    def _next_id_number(self, table: str, prefix: str) -> int:
        row = self.connection.execute(
            f"SELECT COALESCE(MAX(CAST(SUBSTR(id, ?) AS INTEGER)), 0) + 1 "
            f"AS next_number FROM {table}",
            (len(prefix) + 1,),
        ).fetchone()
        return int(row["next_number"])

    def counts(self) -> dict[str, int]:
        return {
            table: int(
                self._row(f"SELECT COUNT(*) AS count FROM {table}")["count"]  # type: ignore[index]
            )
            for table in ("farms", "fields", "tasks", "observations", "sync_events")
        }


demo_repository = DemoRepository()


def reset_demo_data() -> dict[str, int]:
    demo_repository.reset()
    return demo_repository.counts()
