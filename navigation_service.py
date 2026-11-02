import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import networkx as nx

from cv.models import FloorPlan, Route
from graph.graph_builder import NavigationGraphBuilder
from graph.pathfinder import astar_path
from llm.ollama_client import OllamaClient
from llm.query_parser import QueryParser, ParsedQuery
from llm.response_generator import NavigationResponseGenerator

DEFAULT_PROCESSED_DIR = Path("data/processed")


class NavigationService:
    """End-to-end integration service for indoor floor plan navigation."""

    def __init__(
        self,
        floorplan_path: Optional[Path] = None,
        graph_json_path: Optional[Path] = None,
        ollama_client: Optional[OllamaClient] = None,
        auto_load: bool = True,
    ) -> None:
        self.floorplan_path = floorplan_path or (DEFAULT_PROCESSED_DIR / "floorplan.json")
        self.graph_json_path = graph_json_path or (DEFAULT_PROCESSED_DIR / "navigation_graph.json")
        self.ollama_client = ollama_client or OllamaClient()

        self.floorplan: Optional[FloorPlan] = None
        self.graph: Optional[nx.Graph] = None
        self.query_parser: Optional[QueryParser] = None
        self.response_generator: Optional[NavigationResponseGenerator] = None

        if auto_load:
            self.load()

    def load(self) -> None:
        """Load processed FloorPlan and navigation graph from disk.

        Raises
        ------
        FileNotFoundError
            If required processed artifacts are missing.
        """
        if not self.floorplan_path.exists():
            raise FileNotFoundError(
                f"Missing floor plan artifact at '{self.floorplan_path}'. "
                "Please run `python run_phase3.py` to generate the required floorplan.json."
            )

        # The navigation graph is always rebuilt from the FloorPlan's detected
        # connections. ``graph_json_path`` is retained for API compatibility
        # with callers that also persist a graph artifact, but it is not
        # required for navigation.
        #
        # 1. Load FloorPlan
        with open(self.floorplan_path, "r", encoding="utf-8") as f:
            fp_data = json.load(f)
        self.floorplan = FloorPlan.model_validate(fp_data)

        # 2. Build graph from floorplan connections
        builder = NavigationGraphBuilder(self.floorplan)
        self.graph = builder.graph

        # 3. Initialize Parser & Generator
        self.query_parser = QueryParser(
            floorplan=self.floorplan,
            ollama_client=self.ollama_client,
            available_nodes=list(self.graph.nodes()),
        )
        self.response_generator = NavigationResponseGenerator(ollama_client=self.ollama_client)

    def get_available_locations(self) -> List[str]:
        """Return list of known graph node IDs."""
        if self.graph is None:
            return []
        return sorted(list(self.graph.nodes()))

    def set_model(self, model: str) -> None:
        """Switch the LLM model used by this service's parser/generator.

        The query parser and response generator share the same client
        instance, so subsequent navigation requests immediately use the newly
        selected model. Pathfinding and the navigation graph are unaffected.
        """
        self.ollama_client.set_model(model)

    def navigate(self, query: str, use_llm: bool = True) -> Dict[str, Any]:
        """Process a natural-language query and return optimal navigation instructions.

        Workflow:
        1. Parse query to resolve source and destination nodes.
        2. Validate nodes against the loaded navigation graph.
        3. Compute optimal A* path.
        4. Generate structured explanation (LLM or deterministic fallback).
        """
        if self.graph is None or self.query_parser is None or self.response_generator is None:
            raise RuntimeError("NavigationService is not initialized. Call load() first.")

        # Step 1: Query parsing
        parsed: ParsedQuery = self.query_parser.parse(query)
        if not parsed.is_valid or not parsed.source or not parsed.destination:
            return {
                "status": "clarification_needed",
                "query": query,
                "parsed_source": parsed.source,
                "parsed_destination": parsed.destination,
                "message": parsed.clarification_needed or "Could not parse starting and destination locations.",
            }

        # Step 2: A* Pathfinding
        try:
            route: Route = astar_path(self.graph, parsed.source, parsed.destination)
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "source": parsed.source,
                "destination": parsed.destination,
                "message": f"Pathfinding error: {str(e)}",
            }

        # Step 3: Explanation generation
        explanation_res = self.response_generator.generate_explanation(
            route=route,
            floorplan=self.floorplan,
            use_llm=use_llm,
        )

        return {
            "status": "success",
            "query": query,
            "source": route.source,
            "destination": route.destination,
            "path": route.path,
            "doors": route.doors,
            "total_distance": route.total_distance,
            "edge_count": route.edge_count,
            "explanation": explanation_res["explanation"],
            "is_llm_generated": explanation_res["is_llm_generated"],
            "method": explanation_res["method"],
            "route": route.model_dump(),
        }

    def navigate_direct(self, source: str, destination: str, use_llm: bool = True) -> Dict[str, Any]:
        """Direct pathfinding between two known node IDs without NLP parsing."""
        if self.graph is None or self.response_generator is None:
            raise RuntimeError("NavigationService is not initialized. Call load() first.")

        route: Route = astar_path(self.graph, source, destination)
        explanation_res = self.response_generator.generate_explanation(
            route=route,
            floorplan=self.floorplan,
            use_llm=use_llm,
        )

        return {
            "status": "success",
            "source": route.source,
            "destination": route.destination,
            "path": route.path,
            "doors": route.doors,
            "total_distance": route.total_distance,
            "edge_count": route.edge_count,
            "explanation": explanation_res["explanation"],
            "is_llm_generated": explanation_res["is_llm_generated"],
            "method": explanation_res["method"],
            "route": route.model_dump(),
        }
