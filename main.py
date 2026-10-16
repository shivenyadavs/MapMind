import sys
import argparse
from pathlib import Path

from navigation_service import NavigationService
from llm.ollama_client import OllamaClient


def format_navigation_result(res: dict) -> None:
    """Format and print a navigation result clearly to console."""
    print("--------------------------------------------------")
    if res.get("status") == "clarification_needed":
        print("Status:           Clarification Needed")
        print(f"Query:            {res.get('query')}")
        print(f"Message:          {res.get('message')}")
        print("--------------------------------------------------")
        return

    if res.get("status") == "error":
        print("Status:           Error")
        print(f"Query:            {res.get('query')}")
        print(f"Error:            {res.get('message')}")
        print("--------------------------------------------------")
        return

    print(f"Original Query:   {res.get('query')}")
    print(f"Resolved Source:  {res.get('source')}")
    print(f"Resolved Target:  {res.get('destination')}")
    print(f"Computed Path:    {' -> '.join(res.get('path', []))}")
    print(f"Door Sequence:    {res.get('doors', [])}")
    print(f"Route Cost:       {res.get('total_distance', 0.0):.1f} pixels ({res.get('edge_count', 0)} hops)")
    print(f"Generation Mode:  {res.get('method')}")
    print()
    print("Navigation Instructions:")
    print(res.get("explanation"))
    print("--------------------------------------------------")


def run_interactive_mode(service: NavigationService, use_llm: bool = True) -> None:
    """Interactive CLI prompt loop for user queries."""
    print("\n==================================================")
    print("MAPMIND INDOOR NAVIGATION (INTERACTIVE MODE)")
    print("==================================================")
    print("Available locations:", ", ".join(service.get_available_locations()))
    print("Type your query (e.g. 'How do I get from Reception to Room 104?')")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            query = input("MapMind> ").strip()
            if not query:
                continue
            if query.lower() in {"exit", "quit", "q"}:
                print("Exiting MapMind. Goodbye!")
                break
            res = service.navigate(query, use_llm=use_llm)
            format_navigation_result(res)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting MapMind. Goodbye!")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="MapMind: Natural Language Indoor Navigation CLI")
    parser.add_argument("--query", "-q", type=str, help="Natural-language navigation query")
    parser.add_argument("--source", "-s", type=str, help="Direct starting node ID")
    parser.add_argument("--destination", "-d", type=str, help="Direct destination node ID")
    parser.add_argument("--no-llm", action="store_true", help="Force deterministic explanation without LLM")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive navigation session")

    args = parser.parse_args()

    # Check Ollama status
    client = OllamaClient()
    ollama_up, ollama_msg = client.check_availability()
    use_llm = (not args.no_llm)

    print("==================================================")
    print("MAPMIND: INDOOR NAVIGATION ENGINE")
    print("==================================================")
    print(f"Ollama Status: {'AVAILABLE' if ollama_up else 'NOT DETECTED'}")
    if ollama_up:
        print(f"Configured Model: {client.model} (Installed: {client.is_model_installed()})")
    else:
        print(f"Info: {ollama_msg}")
        print("Running in Deterministic Path Explanation Mode.")
    print("==================================================")

    try:
        service = NavigationService(ollama_client=client)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("Please run `python run_phase3.py` first to process the floor plan.")
        sys.exit(1)

    # 1. Interactive Mode
    if args.interactive:
        run_interactive_mode(service, use_llm=use_llm)
        return

    # 2. Direct Source-Destination Mode
    if args.source and args.destination:
        print(f"\nRouting directly: {args.source} -> {args.destination}")
        res = service.navigate_direct(args.source, args.destination, use_llm=use_llm)
        res["query"] = f"{args.source} -> {args.destination}"
        format_navigation_result(res)
        return

    # 3. Single Query Mode
    if args.query:
        print(f"\nProcessing query: \"{args.query}\"")
        res = service.navigate(args.query, use_llm=use_llm)
        format_navigation_result(res)
        return

    # 4. Default Demonstration Mode
    demo_queries = [
        "How do I get from Reception to Room 104?",
        "Navigate from Room 101 to Room 102.",
        "Find a route from Room_1 to Room_5.",
        "Where is Room 103?",
    ]

    print("\n[DEMO] Executing benchmark navigation queries:\n")
    for q in demo_queries:
        res = service.navigate(q, use_llm=use_llm)
        format_navigation_result(res)


if __name__ == "__main__":
    main()
