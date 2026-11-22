"""Where releases, observations, checks and leads are kept, so reporters can query them and every number has a source.

Three stores meet one contract: MemoryStore (the lab), DuckDB (a laptop, the default) and Postgres with PostGIS
(the newsroom server, docker-compose). The same SQL runs on DuckDB and Postgres. A test plays one season through
each store and checks the decisions are identical: the store never changes a decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from .domain import AgsChange, Municipality, Observation, Period


@dataclass
class ReleaseRecord:
    id: int
    source: str
    indicator: str
    period: Period
    received: date
    status: str  # published | quarantined
    checks: list[dict[str, Any]]
    unit: str
    factor: float


class Store(Protocol):
    def put_municipalities(self, ms: list[Municipality], outlines: dict[str, str] | None = None) -> None: ...
    def put_changes(self, cs: list[AgsChange]) -> None: ...
    def changes(self) -> list[AgsChange]: ...
    def municipalities(self) -> dict[str, Municipality]: ...
    def add_release(self, r: ReleaseRecord, rows: list[Observation]) -> int: ...
    def releases(self, indicator: str | None = None) -> list[ReleaseRecord]: ...
    def series(self, indicator: str) -> dict[Period, dict[str, Observation]]: ...
    def put_leads(self, release_id: int, leads: list[dict[str, Any]]) -> None: ...
    def leads(self, release_id: int) -> list[dict[str, Any]]: ...
    def next_id(self) -> int: ...


@dataclass
class MemoryStore:
    _ms: dict[str, Municipality] = field(default_factory=dict)
    _changes: list[AgsChange] = field(default_factory=list)
    _releases: list[ReleaseRecord] = field(default_factory=list)
    _rows: dict[int, list[Observation]] = field(default_factory=dict)
    _leads: dict[int, list[dict[str, Any]]] = field(default_factory=dict)

    def put_municipalities(self, ms: list[Municipality], outlines: dict[str, str] | None = None) -> None:
        self._ms = {m.ags: m for m in ms}

    def put_changes(self, cs: list[AgsChange]) -> None:
        known = {(c.old, c.new, c.valid_from) for c in self._changes}
        self._changes += [c for c in cs if (c.old, c.new, c.valid_from) not in known]

    def changes(self) -> list[AgsChange]:
        return list(self._changes)

    def municipalities(self) -> dict[str, Municipality]:
        return dict(self._ms)

    def next_id(self) -> int:
        return len(self._releases) + 1

    def add_release(self, r: ReleaseRecord, rows: list[Observation]) -> int:
        self._releases.append(r)
        self._rows[r.id] = rows
        return r.id

    def releases(self, indicator: str | None = None) -> list[ReleaseRecord]:
        return [r for r in self._releases if indicator is None or r.indicator == indicator]

    def series(self, indicator: str) -> dict[Period, dict[str, Observation]]:
        latest: dict[Period, ReleaseRecord] = {}
        for r in self._releases:
            if r.indicator == indicator and r.status == "published":
                latest[r.period] = r  # later releases for a period replace earlier ones
        return {p: {o.ags: o for o in self._rows[r.id]} for p, r in latest.items()}

    def put_leads(self, release_id: int, leads: list[dict[str, Any]]) -> None:
        self._leads[release_id] = leads

    def leads(self, release_id: int) -> list[dict[str, Any]]:
        return self._leads.get(release_id, [])


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS municipalities (ags TEXT PRIMARY KEY, name TEXT NOT NULL, population INTEGER NOT NULL,
       kind TEXT NOT NULL, lon DOUBLE PRECISION, lat DOUBLE PRECISION, outline_wkt TEXT)""",
    """CREATE TABLE IF NOT EXISTS ags_changes (old TEXT NOT NULL, new TEXT NOT NULL, valid_from DATE NOT NULL,
       kind TEXT NOT NULL, PRIMARY KEY (old, new, valid_from))""",
    """CREATE TABLE IF NOT EXISTS releases (id INTEGER PRIMARY KEY, source TEXT NOT NULL, indicator TEXT NOT NULL,
       period TEXT NOT NULL, received DATE NOT NULL, status TEXT NOT NULL, checks TEXT NOT NULL, unit TEXT NOT NULL,
       factor DOUBLE PRECISION NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS observations (release_id INTEGER NOT NULL, ags TEXT NOT NULL, period TEXT NOT NULL,
       value DOUBLE PRECISION, flag TEXT, PRIMARY KEY (release_id, ags))""",
    """CREATE TABLE IF NOT EXISTS leads (release_id INTEGER NOT NULL, rank INTEGER NOT NULL, body TEXT NOT NULL,
       PRIMARY KEY (release_id, rank))""",
]


class SqlStore:
    """DuckDB or Postgres through DB-API. Placeholders are written '?' and turned into '%s' for psycopg."""

    def __init__(self, conn: Any, dialect: str) -> None:
        self.conn = conn
        self.dialect = dialect
        for stmt in SCHEMA:
            self._exec(stmt)
        self._commit()  # the tables stand even if the spatial extension below is missing
        self.spatial = False
        if dialect == "postgres":
            try:
                self._exec("CREATE EXTENSION IF NOT EXISTS postgis")
                self._exec("ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326)")
                self.spatial = True
            except Exception:  # plain Postgres without PostGIS: outlines stay as text
                self.conn.rollback()
        self._commit()

    @staticmethod
    def duckdb(path: str = ":memory:") -> SqlStore:
        import duckdb

        return SqlStore(duckdb.connect(path), "duckdb")

    @staticmethod
    def postgres(url: str) -> SqlStore:
        import psycopg

        return SqlStore(psycopg.connect(url), "postgres")

    def _sql(self, q: str) -> str:
        return q.replace("?", "%s") if self.dialect == "postgres" else q

    def _exec(self, q: str, args: tuple[Any, ...] | list[Any] = ()) -> Any:
        cur = self.conn.cursor()
        cur.execute(self._sql(q), args)
        return cur

    def _many(self, q: str, rows: list[tuple[Any, ...]]) -> None:
        if rows:
            cur = self.conn.cursor()
            cur.executemany(self._sql(q), rows)

    def _commit(self) -> None:
        if self.dialect == "postgres":
            self.conn.commit()

    def reset(self) -> None:
        for t in ("leads", "observations", "releases", "ags_changes", "municipalities"):
            self._exec(f"DELETE FROM {t}")
        self._commit()

    def put_municipalities(self, ms: list[Municipality], outlines: dict[str, str] | None = None) -> None:
        self._exec("DELETE FROM municipalities")
        o = outlines or {}
        self._many(
            "INSERT INTO municipalities (ags, name, population, kind, lon, lat, outline_wkt) VALUES (?,?,?,?,?,?,?)",
            [(m.ags, m.name, m.population, m.kind, m.lon, m.lat, o.get(m.ags)) for m in ms],
        )
        if self.spatial:
            self._exec("UPDATE municipalities SET geom = ST_SetSRID(ST_GeomFromText(outline_wkt), 4326) WHERE outline_wkt IS NOT NULL")
        self._commit()

    def touching(self, ags: str) -> list[str]:
        """Neighbours by outline, in the database (PostGIS)."""
        if not self.spatial:
            raise RuntimeError("touching() needs PostGIS")
        cur = self._exec(
            """SELECT b.ags FROM municipalities a JOIN municipalities b ON a.ags <> b.ags
                            AND ST_DWithin(a.geom, b.geom, 1e-6) WHERE a.ags = ? ORDER BY b.ags""",
            (ags,),
        )
        return [r[0] for r in cur.fetchall()]

    def put_changes(self, cs: list[AgsChange]) -> None:
        have = {(c.old, c.new, c.valid_from) for c in self.changes()}
        self._many(
            "INSERT INTO ags_changes (old, new, valid_from, kind) VALUES (?,?,?,?)",
            [(c.old, c.new, c.valid_from, c.kind) for c in cs if (c.old, c.new, c.valid_from) not in have],
        )
        self._commit()

    def changes(self) -> list[AgsChange]:
        rows = self._exec("SELECT old, new, valid_from, kind FROM ags_changes ORDER BY valid_from, old").fetchall()
        return [AgsChange(a, b, d if isinstance(d, date) else date.fromisoformat(str(d)), k) for a, b, d, k in rows]

    def municipalities(self) -> dict[str, Municipality]:
        rows = self._exec("SELECT ags, name, population, lon, lat, kind FROM municipalities").fetchall()
        return {r[0]: Municipality(r[0], r[1], int(r[2]), float(r[3]), float(r[4]), r[5]) for r in rows}

    def next_id(self) -> int:
        return int(self._exec("SELECT COALESCE(MAX(id), 0) + 1 FROM releases").fetchone()[0])

    def add_release(self, r: ReleaseRecord, rows: list[Observation]) -> int:
        self._exec(
            "INSERT INTO releases (id, source, indicator, period, received, status, checks, unit, factor) VALUES (?,?,?,?,?,?,?,?,?)",
            (r.id, r.source, r.indicator, str(r.period), r.received, r.status, json.dumps(r.checks), r.unit, r.factor),
        )
        self._many(
            "INSERT INTO observations (release_id, ags, period, value, flag) VALUES (?,?,?,?,?)",
            [(r.id, o.ags, str(o.period), o.value, o.flag) for o in rows],
        )
        self._commit()
        return r.id

    def releases(self, indicator: str | None = None) -> list[ReleaseRecord]:
        q = "SELECT id, source, indicator, period, received, status, checks, unit, factor FROM releases"
        args: tuple[Any, ...] = ()
        if indicator:
            q += " WHERE indicator = ?"
            args = (indicator,)
        rows = self._exec(q + " ORDER BY id", args).fetchall()
        return [
            ReleaseRecord(
                int(i),
                s,
                ind,
                Period.parse(p),
                d if isinstance(d, date) else date.fromisoformat(str(d)),
                st,
                json.loads(c),
                u,
                float(f),
            )
            for i, s, ind, p, d, st, c, u, f in rows
        ]

    def series(self, indicator: str) -> dict[Period, dict[str, Observation]]:
        rows = self._exec(
            """SELECT o.period, o.ags, o.value, o.flag FROM observations o
               JOIN (SELECT period, MAX(id) AS id FROM releases WHERE indicator = ? AND status = 'published' GROUP BY period) l
               ON o.release_id = l.id""",
            (indicator,),
        ).fetchall()
        out: dict[Period, dict[str, Observation]] = {}
        for p, a, v, f in rows:
            per = Period.parse(p)
            out.setdefault(per, {})[a] = Observation(a, per, None if v is None else float(v), f)
        return out

    def put_leads(self, release_id: int, leads: list[dict[str, Any]]) -> None:
        self._many(
            "INSERT INTO leads (release_id, rank, body) VALUES (?,?,?)",
            [(release_id, i + 1, json.dumps(ld, ensure_ascii=False, default=str)) for i, ld in enumerate(leads)],
        )
        self._commit()

    def leads(self, release_id: int) -> list[dict[str, Any]]:
        rows = self._exec("SELECT body FROM leads WHERE release_id = ? ORDER BY rank", (release_id,)).fetchall()
        return [json.loads(r[0]) for r in rows]
