import re
import json
from typing import Dict, Optional, List, Tuple, Any
from pydantic import BaseModel, Field

from cv.models import FloorPlan
from .ollama_client import OllamaClient, OllamaError


class ParsedQuery(BaseModel):
    """Structured representation of a parsed natural language navigation query."""
    raw_query: str
    source: Optional[str] = None
    destination: Optional[str] = None
    is_valid: bool = False
    clarification_needed: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class QueryParser:
    """Parses natural-language queries into validated source and destination graph node IDs."""

    def __init__(
        self,
        floorplan: Optional[FloorPlan] = None,
        ollama_client: Optional[OllamaClient] = None,
        available_nodes: Optional[List[str]] = None,
    ) -> None:
        self.floorplan = floorplan
        self.ollama_client = ollama_client
        self.available_nodes = set(available_nodes or [])

        # Build comprehensive alias mapping
        self.alias_map: Dict[str, str] = {}
        self._build_alias_map()

    def _build_alias_map(self) -> None:
        """Construct dictionary mapping aliases and room names to canonical node IDs."""
        if self.floorplan:
            for r in self.floorplan.rooms:
                self.available_nodes.add(r.name)
                # Map exact name: "Room_1" -> "Room_1"
                self.alias_map[r.name.lower()] = r.name
                # Map spaced name: "room 1" -> "Room_1", "room1" -> "Room_1"
                norm = r.name.lower().replace("_", " ")
                self.alias_map[norm] = r.name
                self.alias_map[norm.replace(" ", "")] = r.name

            for c in self.floorplan.corridors:
                self.available_nodes.add(c.name)
                self.alias_map[c.name.lower()] = c.name
                norm = c.name.lower().replace("_", " ")
                self.alias_map[norm] = c.name
                self.alias_map[norm.replace(" ", "")] = c.name
                self.alias_map["corridor"] = c.name
                self.alias_map["hallway"] = c.name

        # Standard architectural aliases for the canonical MapMind sample plan
        sample_aliases = {
            "reception": "Room_1",
            "front desk": "Room_1",
            "lobby": "Room_1",
            "room 101": "Room_2",
            "r101": "Room_2",
            "101": "Room_2",
            "room 102": "Room_3",
            "r102": "Room_3",
            "102": "Room_3",
            "room 103": "Room_4",
            "r103": "Room_4",
            "103": "Room_4",
            "room 104": "Room_5",
            "r104": "Room_5",
            "104": "Room_5",
        }
        for alias, node_id in sample_aliases.items():
            if node_id in self.available_nodes or not self.available_nodes:
                self.alias_map[alias] = node_id

    def resolve_node_id(self, term: Optional[str]) -> Optional[str]:
        """Resolve a raw room name or term to a canonical graph node ID."""
        if not term:
            return None
        cleaned = term.strip().lower()
        cleaned = re.sub(r"[^\w\s]", "", cleaned).strip()

        # Direct alias lookup
        if cleaned in self.alias_map:
            return self.alias_map[cleaned]

        # Check partial variations (e.g. "room_1" vs "room 1")
        alt = cleaned.replace("_", " ")
        if alt in self.alias_map:
            return self.alias_map[alt]

        alt2 = cleaned.replace(" ", "_")
        if alt2 in self.alias_map:
            return self.alias_map[alt2]

        return None

    def _parse_deterministically(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract candidate source and destination using robust regex patterns."""
        q = query.strip()

        # Pattern 1: from X to Y
        m = re.search(r"\bfrom\s+(?P<src>.+?)\s+to\s+(?P<dst>[^.?!]+)", q, re.IGNORECASE)
        if m:
            return m.group("src").strip(), m.group("dst").strip()

        # Pattern 2: navigate / route between X and Y
        m = re.search(r"\b(?:between|connecting)\s+(?P<src>.+?)\s+and\s+(?P<dst>[^.?!]+)", q, re.IGNORECASE)
        if m:
            return m.group("src").strip(), m.group("dst").strip()

        # Pattern 3: navigate X to Y
        m = re.search(r"\b(?:navigate|route|go)\s+(?P<src>.+?)\s+to\s+(?P<dst>[^.?!]+)", q, re.IGNORECASE)
        if m:
            return m.group("src").strip(), m.group("dst").strip()

        # Pattern 4: "where is X" / "how to get to X"
        m = re.search(r"\b(?:where is|how to get to|find|locate)\s+(?P<dst>[^.?!]+)", q, re.IGNORECASE)
        if m:
            return None, m.group("dst").strip()

        return None, None

    def _parse_with_llm(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Use local Ollama to extract source and destination from unstructured phrasing."""
        if not self.ollama_client:
            return None, None

        is_up, _ = self.ollama_client.check_availability()
        if not is_up:
            return None, None

        prompt = (
            f"You are a location entity extractor. Given a user query, extract the starting location "
            f"(source) and target location (destination).\n"
            f"Return ONLY valid JSON in the format: {{\"source\": \"...\", \"destination\": \"...\"}}\n"
            f"If a field is not specified, set it to null.\n"
            f"Known locations: {list(self.available_nodes)}\n"
            f"User Query: \"{query}\"\n"
            f"JSON:"
        )

        try:
            resp = self.ollama_client.generate(prompt=prompt, temperature=0.0)
            # Find JSON block
            json_match = re.search(r"\{.*?\}", resp, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data.get("source"), data.get("destination")
        except Exception:
            pass

        return None, None

    def parse(self, query: str) -> ParsedQuery:
        """Parse natural language query into validated source and destination."""
        raw_src, raw_dst = self._parse_deterministically(query)

        # Fallback to local LLM if deterministic regex didn't extract both
        if (not raw_src or not raw_dst) and self.ollama_client:
            llm_src, llm_dst = self._parse_with_llm(query)
            if not raw_src and llm_src:
                raw_src = llm_src
            if not raw_dst and llm_dst:
                raw_dst = llm_dst

        # Resolve against aliases
        resolved_src = self.resolve_node_id(raw_src)
        resolved_dst = self.resolve_node_id(raw_dst)

        # Handle missing destination
        if not resolved_dst:
            if raw_dst:
                return ParsedQuery(
                    raw_query=query,
                    source=resolved_src,
                    destination=None,
                    is_valid=False,
                    clarification_needed=(
                        f"Unrecognized destination '{raw_dst}'. "
                        f"Please specify a valid destination from: {sorted(list(self.available_nodes))}."
                    ),
                )
            return ParsedQuery(
                raw_query=query,
                source=resolved_src,
                destination=None,
                is_valid=False,
                clarification_needed="Please specify a destination location (e.g. 'to Room 104').",
            )

        # Handle missing source
        if not resolved_src:
            if raw_src:
                return ParsedQuery(
                    raw_query=query,
                    source=None,
                    destination=resolved_dst,
                    is_valid=False,
                    clarification_needed=(
                        f"Unrecognized starting location '{raw_src}'. "
                        f"Please specify a valid start from: {sorted(list(self.available_nodes))}."
                    ),
                )
            return ParsedQuery(
                raw_query=query,
                source=None,
                destination=resolved_dst,
                is_valid=False,
                clarification_needed=(
                    f"Destination identified as '{resolved_dst}'. "
                    f"Please specify where you are starting from (e.g. 'from Reception')."
                ),
            )

        # Both source and destination resolved!
        return ParsedQuery(
            raw_query=query,
            source=resolved_src,
            destination=resolved_dst,
            is_valid=True,
            clarification_needed=None,
            metadata={
                "raw_source": raw_src,
                "raw_destination": raw_dst,
            },
        )
