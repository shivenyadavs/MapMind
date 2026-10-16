"""frontend/app.py — MapMind Streamlit Application (Phase 5)

Entry point:  streamlit run frontend/app.py  (from project root)

Architecture:
- Upload or select the built-in demo floor plan.
- Run the existing CV pipeline (parse_floorplan) per upload, isolated in a
  per-upload temp directory so different uploads never share graph state.
- Display detection results, annotated floor plan, room table.
- Accept natural-language navigation queries, call the existing
  NavigationService, display the route and LLM/deterministic instructions.
- Show the navigation graph (Matplotlib figure) with the route highlighted.
- All business logic is delegated to existing backend modules; no duplicate
  algorithms are implemented here.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so backend modules are importable
# when Streamlit is launched from a different working directory.
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent          # frontend/
_PROJECT_ROOT = _HERE.parent                     # mapmind/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import numpy as np

# Backend imports (all reused from existing phases)
from cv.floorplan_parser import parse_floorplan, save_floorplan_json
from cv.preprocessing import generate_synthetic_floorplan, load_floorplan
from cv.visualization import visualize_floorplan
from graph.graph_builder import NavigationGraphBuilder, save_navigation_graph_json
from graph.graph_visualizer import visualize_navigation_graph
from llm.ollama_client import OllamaClient
from navigation_service import NavigationService

from frontend.ui_helpers import (
    bytes_to_numpy,
    build_graph_figure,
    doors_to_table,
    draw_route_overlay,
    get_session_tmpdir,
    get_upload_workdir,
    numpy_to_bytes,
    numpy_to_pil,
    rooms_to_table,
    upload_hash,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mapmind.app")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_UPLOAD_MB = 20
ALLOWED_TYPES = ["png", "jpg", "jpeg"]
DEMO_QUERIES = [
    "How do I get from Reception to Room 104?",
    "Navigate from Room 101 to Room 102.",
    "Find a route from Room_1 to Room_5.",
    "How do I reach the corridor from Room 103?",
]

# ---------------------------------------------------------------------------
# Streamlit page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MapMind — Indoor Navigation",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "MapMind: Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local LLMs",
    },
)

# ---------------------------------------------------------------------------
# Custom CSS — clean professional look
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
/* ---------- Typography & base ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---------- Header ---------- */
.mapmind-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #0F172A 100%);
    border-radius: 12px;
    padding: 28px 36px;
    margin-bottom: 24px;
    border: 1px solid #1E3A5F;
}
.mapmind-header h1 {
    color: #F8FAFC;
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}
.mapmind-header p {
    color: #94A3B8;
    font-size: 0.92rem;
    margin: 0;
    line-height: 1.5;
}

/* ---------- Metric cards ---------- */
.metric-card {
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-card .val {
    font-size: 2rem;
    font-weight: 700;
    color: #38BDF8;
    line-height: 1;
}
.metric-card .lbl {
    font-size: 0.78rem;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 4px;
}

/* ---------- Status badges ---------- */
.badge-ok  { background:#166534; color:#4ADE80; border-radius:6px; padding:3px 10px; font-size:0.78rem; font-weight:600; }
.badge-warn{ background:#78350F; color:#FCD34D; border-radius:6px; padding:3px 10px; font-size:0.78rem; font-weight:600; }
.badge-err { background:#7F1D1D; color:#FCA5A5; border-radius:6px; padding:3px 10px; font-size:0.78rem; font-weight:600; }

/* ---------- Route card ---------- */
.route-card {
    background: #0F172A;
    border: 1px solid #1E3A8A;
    border-left: 4px solid #3B82F6;
    border-radius: 10px;
    padding: 20px 24px;
    margin: 12px 0;
}
.route-card .path-row {
    font-family: 'Courier New', monospace;
    font-size: 1.05rem;
    color: #FBBF24;
    letter-spacing: 0.03em;
    margin-bottom: 10px;
}
.route-card .meta {
    color: #94A3B8;
    font-size: 0.85rem;
    margin-bottom: 4px;
}

/* ---------- Instruction box ---------- */
.instruction-box {
    background: #0D1B2A;
    border: 1px solid #1E3A5F;
    border-radius: 10px;
    padding: 18px 22px;
    color: #CBD5E1;
    font-size: 0.9rem;
    line-height: 1.7;
    white-space: pre-wrap;
}

/* ---------- Section heading ---------- */
.section-heading {
    font-size: 1.05rem;
    font-weight: 600;
    color: #E2E8F0;
    border-bottom: 1px solid #334155;
    padding-bottom: 6px;
    margin: 20px 0 14px 0;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: #0F172A;
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { color: #CBD5E1 !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ===========================================================================
# SESSION STATE HELPERS
# ===========================================================================

def _init_session():
    """Initialise all required session_state keys on first load."""
    defaults = {
        "floor_source": None,       # "demo" | "upload"
        "upload_hash": None,        # hex digest of uploaded file
        "floorplan": None,          # FloorPlan object (current)
        "graph": None,              # nx.Graph (current)
        "workdir": None,            # Path to per-upload tmp dir
        "orig_img_bytes": None,     # bytes of original floor-plan image (BGR→PNG)
        "annotated_img_bytes": None,
        "route_img_bytes": None,    # bytes with route overlay
        "nav_result": None,         # last navigate() result dict
        "ollama_status": None,      # (bool, str) cached availability
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _clear_nav_state():
    """Reset navigation result when the floor plan changes."""
    st.session_state.nav_result = None
    st.session_state.route_img_bytes = None


def _clear_floorplan_state():
    """Fully reset processing state for a new upload."""
    st.session_state.floorplan = None
    st.session_state.graph = None
    st.session_state.floorplan = None
    st.session_state.orig_img_bytes = None
    st.session_state.annotated_img_bytes = None
    _clear_nav_state()


# ===========================================================================
# OLLAMA STATUS (sidebar)
# ===========================================================================

def _get_ollama_client() -> OllamaClient:
    """Return a cached OllamaClient (one per server process)."""
    if "ollama_client" not in st.session_state:
        st.session_state.ollama_client = OllamaClient()
    return st.session_state.ollama_client


def _render_ollama_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 Ollama Status")

    client = _get_ollama_client()
    is_up, msg = client.check_availability(force_refresh=True)
    st.session_state.ollama_status = (is_up, msg)

    if is_up:
        model_ok = client.is_model_installed()
        st.sidebar.markdown(
            f'<span class="badge-ok">● Server reachable</span>', unsafe_allow_html=True
        )
        st.sidebar.caption(f"Model: `{client.model}`")
        if model_ok:
            st.sidebar.markdown(
                '<span class="badge-ok">● Model installed</span>', unsafe_allow_html=True
            )
        else:
            st.sidebar.markdown(
                f'<span class="badge-warn">⚠ Model not found</span>', unsafe_allow_html=True
            )
            st.sidebar.caption(f"Run: `ollama pull {client.model}`")

        # Show all installed models
        try:
            installed = client.list_models()
            if installed:
                st.sidebar.caption("Installed models:")
                for m in installed:
                    marker = "✓ " if m.lower().startswith(client.model.lower().split(":")[0]) else "  "
                    st.sidebar.caption(f"&nbsp;&nbsp;{marker}{m}")
        except Exception:
            pass
    else:
        st.sidebar.markdown(
            '<span class="badge-err">✗ Server not detected</span>', unsafe_allow_html=True
        )
        st.sidebar.caption("Start Ollama with: `ollama serve`")
        st.sidebar.caption("Navigation will use deterministic fallback.")


# ===========================================================================
# FLOOR PLAN PROCESSING
# ===========================================================================

def _process_floorplan(image_path: Path, workdir: Path):
    """Run the CV pipeline on *image_path*; save results to *workdir*.

    All file I/O is redirected to the isolated workdir so the built-in demo
    artifacts in data/processed/ are never overwritten.

    On success, populates session_state: floorplan, graph,
    orig_img_bytes, annotated_img_bytes.
    On failure, raises an exception — caller handles user messaging.
    """
    # 1. Load original image
    orig_img = load_floorplan(image_path)

    # 2. Run full CV + graph pipeline (parse_floorplan saves debug images to
    #    data/processed/ by default; we pass a custom output path to avoid
    #    clobbering the demo artifacts).
    #
    #    parse_floorplan() internally calls save_image() which writes to
    #    data/processed/*.  We use a monkeypatching approach: temporarily
    #    override the save target inside cv.preprocessing.
    import cv.preprocessing as _prep
    _original_processed = _prep.PROCESSED_DATA_DIR
    _prep.PROCESSED_DATA_DIR = workdir   # redirect debug images

    try:
        fp = parse_floorplan(image_path)
    finally:
        _prep.PROCESSED_DATA_DIR = _original_processed  # always restore

    # 3. Save structured JSON to workdir (not to shared data/processed/)
    save_floorplan_json(fp, workdir / "floorplan.json")

    # 4. Build graph
    builder = NavigationGraphBuilder(fp)
    G = builder.graph
    save_navigation_graph_json(G, workdir / "navigation_graph.json")

    # 5. Annotated floor-plan image
    ann_img = visualize_floorplan(fp, orig_img)

    # 6. Store in session state
    st.session_state.floorplan = fp
    st.session_state.graph = G
    st.session_state.orig_img_bytes = numpy_to_bytes(orig_img)
    st.session_state.annotated_img_bytes = numpy_to_bytes(ann_img)

    log.info(
        "Processed floor plan: %d rooms, %d doors, %d corridors, %d walls, %d connections",
        len(fp.rooms), len(fp.doors), len(fp.corridors), len(fp.walls), len(fp.connections),
    )


# ===========================================================================
# SIDEBAR — Upload / Demo selector
# ===========================================================================

def render_sidebar():
    st.sidebar.markdown("## 🗺️ MapMind")
    st.sidebar.markdown(
        "Vision-based indoor floor plan understanding and natural language navigation."
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📂 Floor Plan Source")

    source_choice = st.sidebar.radio(
        "Select floor plan source:",
        options=["Built-in Demo", "Upload Your Own"],
        index=0,
        key="source_radio",
    )

    if source_choice == "Built-in Demo":
        if st.sidebar.button("▶ Load Demo Floor Plan", use_container_width=True):
            _clear_floorplan_state()
            tmpdir = get_session_tmpdir() / "demo"
            tmpdir.mkdir(exist_ok=True)
            with st.spinner("Generating synthetic floor plan and running CV pipeline…"):
                try:
                    sample_path = generate_synthetic_floorplan()
                    _process_floorplan(sample_path, tmpdir)
                    st.session_state.floor_source = "demo"
                    st.session_state.upload_hash = "demo"
                    st.session_state.workdir = tmpdir
                    st.sidebar.success("Demo floor plan loaded.")
                except Exception as exc:
                    log.exception("Demo processing failed")
                    st.sidebar.error(f"Failed to load demo: {exc}")

    else:  # Upload
        uploaded = st.sidebar.file_uploader(
            "Upload floor plan image",
            type=ALLOWED_TYPES,
            help=f"PNG, JPG, or JPEG · Max {MAX_UPLOAD_MB} MB",
        )
        if uploaded is not None:
            raw_bytes = uploaded.read()

            # Validate size
            if len(raw_bytes) > MAX_UPLOAD_MB * 1024 * 1024:
                st.sidebar.error(f"File exceeds {MAX_UPLOAD_MB} MB limit.")
                return

            # Validate decodability
            try:
                _ = bytes_to_numpy(raw_bytes)
            except ValueError:
                st.sidebar.error("Cannot decode image. Please upload a valid PNG or JPEG.")
                return

            h = upload_hash(raw_bytes)

            # Only re-process if this is a new upload
            if st.session_state.upload_hash != h:
                _clear_floorplan_state()
                tmpdir = get_upload_workdir(get_session_tmpdir(), h)

                # Save raw upload to workdir
                ext = Path(uploaded.name).suffix or ".png"
                img_path = tmpdir / f"upload{ext}"
                img_path.write_bytes(raw_bytes)

                with st.spinner("Running CV pipeline on uploaded floor plan…"):
                    try:
                        _process_floorplan(img_path, tmpdir)
                        st.session_state.floor_source = "upload"
                        st.session_state.upload_hash = h
                        st.session_state.workdir = tmpdir
                        st.sidebar.success("Floor plan processed successfully.")
                    except Exception as exc:
                        log.exception("Upload processing failed")
                        st.sidebar.error(f"Processing failed: {exc}")
                        # Do NOT silently fall back to demo
                        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Processing Info")
    if st.session_state.floorplan:
        fp = st.session_state.floorplan
        st.sidebar.caption(
            f"Image: {fp.image_width} × {fp.image_height} px\n"
            f"Rooms: {len(fp.rooms)} | Corridors: {len(fp.corridors)}\n"
            f"Doors: {len(fp.doors)} | Walls: {len(fp.walls)}"
        )
    else:
        st.sidebar.caption("No floor plan loaded yet.")

    _render_ollama_sidebar()


# ===========================================================================
# MAIN CONTENT — Detection panel
# ===========================================================================

def render_detection_panel():
    fp: Optional = st.session_state.floorplan

    if fp is None:
        st.info(
            "**No floor plan loaded.**\n\n"
            "Use the sidebar to load the built-in demo or upload your own floor-plan image."
        )
        return

    # -----------------------------------------------------------------------
    # Detection metric row
    # -----------------------------------------------------------------------
    st.markdown('<div class="section-heading">Detection Results</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    metrics = [
        ("Rooms", len(fp.rooms)),
        ("Corridors", len(fp.corridors)),
        ("Doors", len(fp.doors)),
        ("Walls", len(fp.walls)),
        ("Connections", len(fp.connections)),
    ]
    for col, (label, val) in zip(cols, metrics):
        col.markdown(
            f'<div class="metric-card"><div class="val">{val}</div>'
            f'<div class="lbl">{label}</div></div>',
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------------------------
    # Floor plan images: original + annotated
    # -----------------------------------------------------------------------
    st.markdown('<div class="section-heading">Floor Plan Visualization</div>', unsafe_allow_html=True)
    c_orig, c_ann = st.columns(2)
    with c_orig:
        st.markdown("**Original Floor Plan**")
        if st.session_state.orig_img_bytes:
            st.image(st.session_state.orig_img_bytes, use_container_width=True)
    with c_ann:
        st.markdown("**Annotated Detections**")
        if st.session_state.annotated_img_bytes:
            st.image(st.session_state.annotated_img_bytes, use_container_width=True)
        st.caption(
            "🟩 Rooms&nbsp;&nbsp; 🟨 Corridors&nbsp;&nbsp; 🟣 Doors (D#)&nbsp;&nbsp; 🔴 Walls"
        )

    # -----------------------------------------------------------------------
    # Debug images expandable section
    # -----------------------------------------------------------------------
    workdir: Optional[Path] = st.session_state.workdir
    if workdir:
        debug_files = {
            "Rooms Debug": workdir / "rooms_debug.png",
            "Doors Debug": workdir / "doors_debug.png",
            "Corridors Debug": workdir / "corridors_debug.png",
            "Walls Debug": workdir / "walls_debug.png",
        }
        available_debug = {k: p for k, p in debug_files.items() if p.exists()}
        if available_debug:
            with st.expander("🔍 Debug Visualizations", expanded=False):
                dcols = st.columns(len(available_debug))
                for col, (label, path) in zip(dcols, available_debug.items()):
                    with col:
                        st.markdown(f"**{label}**")
                        st.image(str(path), use_container_width=True)

    # -----------------------------------------------------------------------
    # Detected Rooms Explorer
    # -----------------------------------------------------------------------
    st.markdown('<div class="section-heading">Detected Regions</div>', unsafe_allow_html=True)

    tab_rooms, tab_doors, tab_connections = st.tabs(["Rooms & Corridors", "Doors", "Connections"])

    with tab_rooms:
        room_rows = rooms_to_table(fp)
        if room_rows:
            st.dataframe(
                room_rows,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("Node ID"),
                    "Type": st.column_config.TextColumn("Type"),
                    "Area (px²)": st.column_config.NumberColumn("Area (px²)", format="%d"),
                },
            )
            st.caption(
                "⚠️ Room IDs are assigned automatically by the CV pipeline (Region_1, Room_2 …). "
                "Semantic names (Reception, Room 101 …) are resolved via the query parser's alias map."
            )
        else:
            st.warning("No rooms or corridors detected.")

    with tab_doors:
        door_rows = doors_to_table(fp)
        if door_rows:
            st.dataframe(door_rows, use_container_width=True, hide_index=True)
        else:
            st.warning("No doors detected.")

    with tab_connections:
        if fp.connections:
            conn_rows = [
                {
                    "From": c.source,
                    "To": c.destination,
                    "Via Door": c.via_door,
                    "Distance (px)": round(c.distance, 1),
                }
                for c in fp.connections
            ]
            st.dataframe(conn_rows, use_container_width=True, hide_index=True)
        else:
            st.warning("No connections detected. Navigation may not be available.")


# ===========================================================================
# NAVIGATION PANEL
# ===========================================================================

def render_navigation_panel():
    fp = st.session_state.floorplan
    G = st.session_state.graph

    st.markdown('<div class="section-heading">Natural-Language Navigation</div>', unsafe_allow_html=True)

    if fp is None or G is None:
        st.info("Load a floor plan first to enable navigation.")
        return

    if G.number_of_edges() == 0:
        st.warning(
            "The navigation graph has no edges — no door connections were detected. "
            "Navigation is not possible with this floor plan."
        )
        return

    # -----------------------------------------------------------------------
    # Ollama status notice
    # -----------------------------------------------------------------------
    ollama_status = st.session_state.ollama_status
    if ollama_status and not ollama_status[0]:
        st.info(
            "ℹ️ Ollama server not detected — navigation will use **deterministic fallback** mode. "
            "Route calculations are unaffected; only the instruction style changes.",
            icon="ℹ️",
        )

    # -----------------------------------------------------------------------
    # Query input + example buttons
    # -----------------------------------------------------------------------
    st.markdown("**Enter a navigation query:**")
    query_input = st.text_input(
        label="Navigation query",
        value=st.session_state.get("nav_query_input", ""),
        placeholder='e.g. "How do I get from Reception to Room 104?"',
        label_visibility="collapsed",
        key="nav_query_input",
    )

    st.markdown("**Quick examples:**")
    eq_cols = st.columns(len(DEMO_QUERIES))
    for col, example in zip(eq_cols, DEMO_QUERIES):
        if col.button(f'"{example}"', key=f"eq_{hash(example)}", use_container_width=True):
            st.session_state.nav_query_input = example
            st.rerun()

    nav_submit = st.button("🧭 Navigate", type="primary", use_container_width=False)

    if nav_submit and query_input.strip():
        _run_navigation(query_input.strip(), fp, G)
    elif nav_submit:
        st.warning("Please enter a navigation query.")

    # Render result if available
    if st.session_state.nav_result:
        _render_nav_result()


def _run_navigation(query: str, fp, G):
    """Call the existing NavigationService and store result in session state."""
    client = _get_ollama_client()
    is_up, _ = client.check_availability()

    with st.spinner("Computing route…"):
        try:
            service = NavigationService(
                floorplan_path=st.session_state.workdir / "floorplan.json",
                graph_json_path=st.session_state.workdir / "navigation_graph.json",
                ollama_client=client,
                auto_load=True,
            )
            result = service.navigate(query, use_llm=is_up)
            result["query"] = query
            st.session_state.nav_result = result

            # Build route overlay image
            if result.get("status") == "success":
                from cv.models import Route
                route = Route(**result["route"]) if isinstance(result.get("route"), dict) else None
                if route:
                    import cv2
                    ann_img = cv2.imdecode(
                        np.frombuffer(st.session_state.annotated_img_bytes, np.uint8),
                        cv2.IMREAD_COLOR,
                    )
                    overlay = draw_route_overlay(ann_img, fp, route)
                    st.session_state.route_img_bytes = numpy_to_bytes(overlay)
        except FileNotFoundError:
            st.session_state.nav_result = {
                "status": "error",
                "query": query,
                "message": "Floor plan artifacts not found. Please re-process the floor plan.",
            }
        except Exception as exc:
            log.exception("Navigation error")
            st.session_state.nav_result = {
                "status": "error",
                "query": query,
                "message": f"Navigation error: {exc}",
            }


def _render_nav_result():
    res = st.session_state.nav_result
    if not res:
        return

    status = res.get("status")

    if status == "clarification_needed":
        st.warning(f"**Clarification needed:** {res.get('message', '')}")
        return

    if status == "error":
        st.error(f"**Error:** {res.get('message', '')}")
        return

    # Success
    path = res.get("path", [])
    doors = res.get("doors", [])
    dist = res.get("total_distance", 0.0)
    hops = res.get("edge_count", 0)
    method = res.get("method", "unknown")
    is_llm = res.get("is_llm_generated", False)

    # ---- Route summary card ----
    path_arrow = " → ".join(path) if path else "—"
    doors_str = " → ".join(doors) if doors else "None"

    st.markdown(
        f"""
<div class="route-card">
  <div class="path-row">🗺️ {path_arrow}</div>
  <div class="meta">🚪 Doors: {doors_str}</div>
  <div class="meta">📏 Route cost: <strong>{dist:.1f} pixels</strong> · {hops} hop(s)</div>
  <div class="meta">🤖 Instructions: <strong>{'LLM (' + method + ')' if is_llm else 'Deterministic fallback'}</strong></div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not is_llm and method and "ollama" not in method.lower():
        st.caption("ℹ️ Deterministic instructions shown — Ollama unavailable or generation timed out.")

    # ---- Navigation instructions ----
    st.markdown("**Navigation Instructions**")
    explanation = res.get("explanation", "")
    st.markdown(
        f'<div class="instruction-box">{explanation}</div>',
        unsafe_allow_html=True,
    )

    st.caption(
        "⚠️ Route cost is measured in image pixels and is a relative estimate only. "
        "No metric scale (metres) is available for this floor plan."
    )

    # ---- Route visualizations ----
    st.markdown('<div class="section-heading">Route Visualization</div>', unsafe_allow_html=True)

    col_route, col_graph = st.columns([1, 1])

    with col_route:
        st.markdown("**Route Overlay on Floor Plan**")
        if st.session_state.route_img_bytes:
            st.image(st.session_state.route_img_bytes, use_container_width=True)
            st.caption(
                "🟢 Source  🔴 Destination  🟡 Intermediate  🔵 Route doors  ↗ Direction"
            )
        else:
            st.info("Route image not available.")

    with col_graph:
        st.markdown("**Navigation Graph (Route Highlighted)**")
        fp = st.session_state.floorplan
        G = st.session_state.graph
        if fp and G:
            fig = build_graph_figure(G, fp, highlighted_path=path)
            st.pyplot(fig, use_container_width=True)
            plt_import = fig  # keep reference to close
            import matplotlib.pyplot as plt_mod
            plt_mod.close(fig)


# ===========================================================================
# GRAPH PANEL (standalone tab view)
# ===========================================================================

def render_graph_panel():
    st.markdown('<div class="section-heading">Navigation Graph</div>', unsafe_allow_html=True)

    fp = st.session_state.floorplan
    G = st.session_state.graph

    if fp is None or G is None:
        st.info("Load a floor plan to see the navigation graph.")
        return

    col_info, col_graph = st.columns([1, 2])

    with col_info:
        st.markdown("**Graph Statistics**")
        st.metric("Nodes", G.number_of_nodes())
        st.metric("Edges", G.number_of_edges())

        # Node type breakdown
        rooms_count = sum(1 for _, d in G.nodes(data=True) if d.get("type") == "room")
        corr_count = sum(1 for _, d in G.nodes(data=True) if d.get("type") == "corridor")
        st.caption(f"Room nodes: {rooms_count} | Corridor nodes: {corr_count}")

        st.markdown("**Nodes**")
        for node_id, data in G.nodes(data=True):
            node_type = data.get("type", "?")
            center = data.get("center", (0, 0))
            st.markdown(f"- `{node_id}` ({node_type}) — centre {center}")

        st.markdown("**Edges**")
        for u, v, data in G.edges(data=True):
            door = data.get("door_id", "—")
            dist = data.get("distance", 0.0)
            st.markdown(f"- `{u}` ↔ `{v}` | {door} | {dist:.0f} px")

    with col_graph:
        import matplotlib.pyplot as plt_mod
        fig = build_graph_figure(G, fp, highlighted_path=[])
        st.pyplot(fig, use_container_width=True)
        plt_mod.close(fig)


# ===========================================================================
# MAIN LAYOUT
# ===========================================================================

def main():
    _init_session()

    # Sidebar
    render_sidebar()

    # Header
    st.markdown(
        """
<div class="mapmind-header">
  <h1>🗺️ MapMind</h1>
  <p>
    Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local LLMs<br>
    <small>Phase 1–5 · OpenCV · NetworkX · A* Pathfinding · Ollama (<code>qwen3.5:4b</code>)</small>
  </p>
</div>
""",
        unsafe_allow_html=True,
    )

    # Main tabs
    tab_detect, tab_navigate, tab_graph = st.tabs(
        ["🔍 Detection", "🧭 Navigation", "📊 Graph"]
    )

    with tab_detect:
        render_detection_panel()

    with tab_navigate:
        render_navigation_panel()

    with tab_graph:
        render_graph_panel()


if __name__ == "__main__":
    main()
