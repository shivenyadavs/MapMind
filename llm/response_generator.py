import re
from typing import Optional, Dict, Any, List
from cv.models import Route, FloorPlan
from .ollama_client import OllamaClient, OllamaError


def _has_grounding_violation(text: str, route: Route) -> bool:
    """Reject LLM text that references places outside the computed route."""
    allowed = set(route.path) | set(route.doors)
    for match in re.finditer(r"\b(Room|Corridor|Door)[ _](\d+)\b", text, re.IGNORECASE):
        reference = f"{match.group(1).title()}_{match.group(2)}"
        if reference not in allowed:
            return True
    if re.search(r"\bturn\s+(left|right)\b", text, re.IGNORECASE):
        return True
    return False


def deterministic_route_explanation(route: Route, floorplan: Optional[FloorPlan] = None) -> str:
    """Generate a reliable, structured deterministic text explanation of a pre-computed route.

    Used when Ollama is unavailable or as a baseline verification.
    """
    if route.source == route.destination:
        return f"You are already at {route.source}. No navigation required."

    # Look up human-readable names if floorplan provided
    room_names = {}
    if floorplan:
        for r in floorplan.rooms:
            room_names[r.name] = r.name
        for c in floorplan.corridors:
            room_names[c.name] = c.name

    steps: List[str] = []
    path = route.path
    doors = route.doors

    steps.append(f"Start in {path[0]}.")

    for idx, (u, v) in enumerate(zip(path[:-1], path[1:]), start=1):
        door_id = doors[idx - 1] if idx - 1 < len(doors) else None
        if door_id:
            steps.append(f"Step {idx}: From {u}, pass through {door_id} into {v}.")
        else:
            steps.append(f"Step {idx}: Move directly from {u} into {v}.")

    steps.append(f"Arrive at destination: {route.destination}.")
    steps.append(
        f"Total estimated travel distance: {route.total_distance:.1f} pixels "
        f"across {len(route.doors)} doorway(s) (pixel-based estimate)."
    )

    return "\n".join(steps)


class NavigationResponseGenerator:
    """Generates natural language explanations of pre-computed graph routes using local LLM."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None) -> None:
        self.ollama_client = ollama_client

    def generate_explanation(
        self,
        route: Route,
        floorplan: Optional[FloorPlan] = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        """Generate a natural language route explanation.

        Parameters
        ----------
        route : Route
            Pre-computed graph route from A* pathfinder.
        floorplan : Optional[FloorPlan]
            Structured floor plan containing geometric context.
        use_llm : bool
            Whether to attempt local Ollama generation (default True).

        Returns
        -------
        Dict[str, Any]
            Dictionary containing 'explanation', 'is_llm_generated', 'route', and 'method'.
        """
        # Always compute the deterministic baseline
        fallback_text = deterministic_route_explanation(route, floorplan)

        if not use_llm or not self.ollama_client:
            return {
                "explanation": fallback_text,
                "is_llm_generated": False,
                "method": "deterministic_fallback",
                "route": route.model_dump(),
            }

        # Check Ollama server availability
        is_up, _ = self.ollama_client.check_availability()
        if not is_up or not self.ollama_client.is_model_installed():
            return {
                "explanation": fallback_text,
                "is_llm_generated": False,
                "method": "deterministic_fallback (Ollama unavailable/model not found)",
                "route": route.model_dump(),
            }

        # Build prompt for Ollama
        system_prompt = (
            "You are MapMind, a helpful indoor floor plan navigation assistant. "
            "Your role is to explain a pre-computed route to the user clearly and concisely.\n"
            "STRICT RULES:\n"
            "1. You MUST follow the EXACT sequence of rooms and doors provided. Do NOT alter the route.\n"
            "2. Do NOT invent new rooms, doors, landmarks, or turns (do NOT claim 'turn left' or 'turn right' "
            "unless explicit directional data is provided; describe the sequence of spaces and doors).\n"
            "3. State clearly that the travel distance is a pixel-based estimate.\n"
            "4. Keep the explanation natural, friendly, and easy to follow."
        )

        user_prompt = (
            f"Please explain this indoor route:\n"
            f"- Starting point: {route.source}\n"
            f"- Final destination: {route.destination}\n"
            f"- Route sequence: {' -> '.join(route.path)}\n"
            f"- Traversed doorways: {route.doors}\n"
            f"- Total distance: {route.total_distance:.1f} pixels\n"
            f"- Number of edges: {route.edge_count}\n\n"
            f"Provide a clear, step-by-step navigation instruction for this path."
        )

        try:
            llm_text = self.ollama_client.generate(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.2,
                timeout=self.ollama_client.timeout,
            )
            if llm_text and not _has_grounding_violation(llm_text, route):
                return {
                    "explanation": llm_text,
                    "is_llm_generated": True,
                    "method": f"ollama ({self.ollama_client.model})",
                    "route": route.model_dump(),
                }
        except Exception:
            # Gracefully fall back to deterministic response on timeout or error
            pass

        return {
            "explanation": fallback_text,
            "is_llm_generated": False,
            "method": "deterministic_fallback",
            "route": route.model_dump(),
        }
