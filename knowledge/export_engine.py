import json
import logging
from typing import Optional

import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_SKIP_KEYS = {"id", "type"}


class ExportEngine:
    def __init__(self, store):
        self._store = store

    def to_json(self, output_path: str) -> None:
        data = {
            "nodes": self._store.get_all_nodes(),
            "edges": self._store.get_all_edges(),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("[ExportEngine] JSON → %s", output_path)

    def to_yaml(self, output_path: str) -> None:
        data = {
            "nodes": self._store.get_all_nodes(),
            "edges": self._store.get_all_edges(),
        }
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=True)
        logger.info("[ExportEngine] YAML → %s", output_path)

    def to_markdown(self, output_path: str) -> None:
        sections = [
            self._section_foundation(),
            self._section_characters(),
            self._section_scenes(),
            self._section_world(),
            self._section_concepts(),
            self._section_documents(),
        ]
        lines: list[str] = []
        for s in sections:
            lines += s
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("[ExportEngine] Markdown → %s", output_path)

    def to_context_pack(self, skill: str, scene_id: str, story_id: str, output_path: str) -> None:
        from knowledge.context_orchestrator import build_context
        pack = build_context(skill=skill, story_id=story_id, scene_id=scene_id)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(pack, f, allow_unicode=True, default_flow_style=False)
        logger.info("[ExportEngine] context pack (%s) → %s", skill, output_path)

    # ------------------------------------------------------------------
    # Section builders (one per node type)
    # ------------------------------------------------------------------

    def _section_foundation(self) -> list[str]:
        stories = self._store.get_nodes_by_type("Story")
        title = stories[0].get("title", "Untitled") if stories else "Untitled"
        out = [f"# Story Bible: {title}\n"]
        if stories:
            out.append("## Story Foundation")
            out += self._props_as_bullets(stories[0])
            out.append("")
        return out

    def _section_characters(self) -> list[str]:
        chars = self._store.get_nodes_by_type("Character")
        if not chars:
            return []
        out = ["## Characters"]
        for c in chars:
            out += self._character_block(c)
        return out

    def _character_block(self, c: dict) -> list[str]:
        out = [f"### {c.get('name', c['id'])} ({c.get('role', '')})"]
        out += self._props_as_bullets(c, skip={"name", "role"})
        out += self._relationship_lines(c["id"])
        out.append("")
        return out

    def _relationship_lines(self, node_id: str) -> list[str]:
        edges = self._store.get_edges_from(node_id)
        if not edges:
            return []
        lines = ["- **Relationships:**"]
        for e in edges:
            target = self._store.get_node(e["to_id"])
            tname = target.get("name", e["to_id"]) if target else e["to_id"]
            lines.append(f"  - {e['rel_type']}: {tname}")
        return lines

    def _section_scenes(self) -> list[str]:
        scenes = self._store.get_nodes_by_type("Scene")
        if not scenes:
            return []
        out = ["## Scenes"]
        for sc in scenes:
            out.append(f"### Scene {sc['id']}: {sc.get('goal', '')}")
            out += self._props_as_bullets(sc, skip={"goal"})
            out.append("")
        return out

    def _section_world(self) -> list[str]:
        locs = self._store.get_nodes_by_type("Location")
        factions = self._store.get_nodes_by_type("Faction")
        if not locs and not factions:
            return []
        out = ["## World"]
        for loc in locs:
            out.append(f"### {loc.get('name', loc['id'])}")
            out += self._props_as_bullets(loc, skip={"name"})
            out.append("")
        for fac in factions:
            out.append(f"### {fac.get('name', fac['id'])}")
            out += self._props_as_bullets(fac, skip={"name"})
            out.append("")
        return out

    def _section_concepts(self) -> list[str]:
        concepts = self._store.get_nodes_by_type("Concept")
        if not concepts:
            return []
        out = ["## Concepts & Themes"]
        for con in concepts:
            out.append(f"### {con.get('name', con['id'])}")
            out += self._props_as_bullets(con, skip={"name"})
            out.append("")
        return out

    def _section_documents(self) -> list[str]:
        docs = self._store.get_nodes_by_type("Document")
        if not docs:
            return []
        out = ["## Prewriting Notes (Raw Agent Output)"]
        for doc in docs:
            out.append(f"### {doc.get('agent', doc['id'])}")
            for line in doc.get("content", "").splitlines():
                out.append(f"> {line}" if line.strip() else ">")
            out.append("")
        return out

    # ------------------------------------------------------------------

    def _props_as_bullets(self, node: dict, skip: Optional[set] = None) -> list[str]:
        excluded = _SKIP_KEYS | (skip or set())
        return [
            f"- **{k.replace('_', ' ').title()}:** {v}"
            for k, v in node.items()
            if k not in excluded and v
        ]
