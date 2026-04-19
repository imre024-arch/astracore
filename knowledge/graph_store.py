import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class GraphStore:
    def __init__(self, story_id: str):
        agents_path = Path(os.getenv("AGENTS_REPO_PATH", "."))
        db_dir = agents_path / "knowledge" / story_id
        db_dir.mkdir(parents=True, exist_ok=True)
        self._path = db_dir / "graph.db"
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        logger.info("[GraphStore] Opened %s", self._path)

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id          TEXT PRIMARY KEY,
                type        TEXT NOT NULL,
                properties  TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS edges (
                id          TEXT PRIMARY KEY,
                from_id     TEXT NOT NULL,
                rel_type    TEXT NOT NULL,
                to_id       TEXT NOT NULL,
                properties  TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
            CREATE INDEX IF NOT EXISTS idx_edges_to   ON edges(to_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
        """)
        self._conn.commit()

    def add_node(self, node_id: str, node_type: str, properties: dict) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO nodes (id, type, properties) VALUES (?, ?, ?)",
            (node_id, node_type, json.dumps(properties, ensure_ascii=False)),
        )
        self._conn.commit()
        logger.debug("[GraphStore] node %s (%s)", node_id, node_type)

    def add_edge(self, from_id: str, rel_type: str, to_id: str, properties: dict = None) -> None:
        self._conn.execute(
            "INSERT INTO edges (id, from_id, rel_type, to_id, properties) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), from_id, rel_type, to_id, json.dumps(properties or {}, ensure_ascii=False)),
        )
        self._conn.commit()
        logger.debug("[GraphStore] edge %s -[%s]-> %s", from_id, rel_type, to_id)

    def get_node(self, node_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        return self._deserialize(row) if row else None

    def get_nodes_by_type(self, node_type: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM nodes WHERE type = ?", (node_type,)
        ).fetchall()
        return [self._deserialize(r) for r in rows]

    def get_all_nodes(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        return [self._deserialize(r) for r in rows]

    def get_all_edges(self) -> list[dict]:
        rows = self._conn.execute("SELECT * FROM edges").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d.update(json.loads(d.pop("properties", "{}")))
            result.append(d)
        return result

    def get_neighbors(self, node_id: str, rel_type: str = None, direction: str = "out") -> list[dict]:
        results = []
        if direction in ("out", "both"):
            q = "SELECT n.* FROM nodes n JOIN edges e ON n.id = e.to_id WHERE e.from_id = ?"
            params: list = [node_id]
            if rel_type:
                q += " AND e.rel_type = ?"
                params.append(rel_type)
            results += self._conn.execute(q, params).fetchall()
        if direction in ("in", "both"):
            q = "SELECT n.* FROM nodes n JOIN edges e ON n.id = e.from_id WHERE e.to_id = ?"
            params = [node_id]
            if rel_type:
                q += " AND e.rel_type = ?"
                params.append(rel_type)
            results += self._conn.execute(q, params).fetchall()
        return [self._deserialize(r) for r in results]

    def get_edges_from(self, node_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE from_id = ?", (node_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def _deserialize(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d.update(json.loads(d.pop("properties", "{}")))
        return d

    def close(self) -> None:
        self._conn.close()
