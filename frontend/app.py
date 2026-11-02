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

import html
import logging
import sys
import time
from pathlib import Path
from typing import Optional

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
from cv.coordinates import scale_floorplan_to_source
from cv.floorplan_parser import parse_floorplan
from cv.preprocessing import generate_synthetic_floorplan, load_floorplan
from cv.visualization import visualize_floorplan
from graph.graph_builder import NavigationGraphBuilder, save_navigation_graph_json
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
        "floorplan": None,          # FloorPlan object (current, working coordinates)
        "floorplan_source": None,   # FloorPlan expressed in original-image coordinates
        "graph": None,              # nx.Graph (current)
        "workdir": None,            # Path to per-upload tmp dir
        "orig_img_bytes": None,     # bytes of original floor-plan image (BGR→PNG)
        "annotated_img_bytes": None,
        "route_img_bytes": None,    # bytes with route overlay
        "nav_result": None,         # last navigate() result dict
        "ollama_status": None,      # (bool, str) cached availability
        "nav_query_input": "",      # navigation query text (widget state)
        # Ollama model discovery / selection (session-scoped; never written to .env)
        "selected_model": None,
        "available_models": [],
        "model_details": {},
        "models_initialized": False,
        "model_list_error": None,
        "model_notice": None,
        "model_test_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# Keys that hold per-floor-plan processing results. They must all be cleared
# together whenever the active floor plan changes or processing fails, so the
# UI can never show a stale route or stale images.
PROCESSING_STATE_KEYS = (
    "floorplan",
    "floorplan_source",
    "graph",
    "workdir",
    "floor_source",
    "orig_img_bytes",
    "annotated_img_bytes",
    "route_img_bytes",
    "nav_result",
)


def _reset_processing_state(state) -> None:
    """Clear processed floor-plan state from a mapping-like object.

    Extracted as a pure helper so it can be unit-tested without a Streamlit
    runtime. ``upload_hash`` is intentionally not cleared: the upload handler
    owns that key and uses it to avoid reprocessing a failed upload on every
    rerun.
    """
    for key in PROCESSING_STATE_KEYS:
        state[key] = None


def _clear_floorplan_state():
    """Fully reset per-floor-plan processing state."""
    _reset_processing_state(st.session_state)


def _begin_upload(state, new_hash: str) -> bool:
    """Begin processing an upload exactly once.

    Clears any previous floor-plan/navigation results and records the hash
    *before* processing starts. If processing fails, the hash remains set so
    the same failed file is not retried on every Streamlit rerun.

    Returns True when the caller should process the upload, False when this
    exact upload was already attempted.
    """
    if state.get("upload_hash") == new_hash:
        return False
    _reset_processing_state(state)
    state["upload_hash"] = new_hash
    return True


def _set_nav_query(text: str) -> None:
    """Set the navigation query input from a quick-example button.

    Implemented as a widget callback so it runs before the text input is
    instantiated in the next script run. Assigning the key directly inside
    the button branch (after the widget exists) raises StreamlitAPIException.
    """
    st.session_state["nav_query_input"] = text


def _retry_upload() -> None:
    """Forget the failed upload hash so the next rerun processes it again."""
    st.session_state["upload_hash"] = None


# ===========================================================================
# OLLAMA MODEL CONFIGURATION (sidebar)
# ===========================================================================

def _get_ollama_client() -> OllamaClient:
    """Return the session's OllamaClient, synced to the selected model.

    The client is reused so its short-lived status/model caches survive normal
    Streamlit reruns. Its ``model`` property is updated from session state on
    every call, so changing the dropdown immediately affects all subsequent
    requests without recreating the client or mutating environment variables.
    """
    client = st.session_state.get("ollama_client")
    if client is None:
        client = OllamaClient()
        st.session_state.ollama_client = client

    selected = st.session_state.get("selected_model")
    if selected and client.model != selected:
        client.set_model(selected)
    return client


def _apply_selected_model() -> None:
    """Push the current dropdown selection into the shared Ollama client."""
    selected = st.session_state.get("selected_model")
    if selected:
        _get_ollama_client().set_model(selected)


def _format_model_size(size) -> Optional[str]:
    """Format Ollama's byte size for display, or return None if unavailable."""
    if not isinstance(size, (int, float)) or isinstance(size, bool) or size <= 0:
        return None
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024
    return None


def _reconcile_selected_model(client: OllamaClient) -> None:
    """Keep the selected model valid after a discovery refresh.

    - Preserve the current selection if it is still installed.
    - On the first load, prefer the configured/default model when installed.
    - If the current model was removed, select the first available model and
      record a user-visible notice.
    - If discovery failed (offline), retain the previous selection so it can
      be restored after Ollama comes back.
    """
    names = list(st.session_state.get("available_models") or [])
    current = st.session_state.get("selected_model")
    list_error = st.session_state.get("model_list_error")

    if not names:
        if list_error is None:
            st.session_state.selected_model = None
            if current:
                st.session_state.model_notice = (
                    f"Previously selected model `{current}` is no longer installed. "
                    "No Ollama models are currently available."
                )
        return

    if current in names:
        st.session_state.selected_model = current
        return

    preferred = current or client.model
    fallback = preferred if preferred in names else names[0]

    if current and current not in names:
        st.session_state.model_notice = (
            f"Previously selected model `{current}` is no longer installed. "
            f"Switched to `{fallback}`."
        )
    elif not current and preferred not in names:
        st.session_state.model_notice = (
            f"Configured model `{preferred}` is not installed. Using `{fallback}` instead."
        )

    st.session_state.selected_model = fallback


def _load_models(*, force_refresh: bool = False, notify: bool = False) -> None:
    """Discover installed Ollama models and reconcile the current selection.

    Called once per session at startup, and explicitly by the refresh button.
    Ordinary reruns use the cached list stored in session state and do not
    issue synchronous HTTP requests.
    """
    client = _get_ollama_client()
    try:
        details = client.list_model_details(force_refresh=force_refresh)
    except Exception as exc:
        st.session_state.available_models = []
        st.session_state.model_details = {}
        st.session_state.model_list_error = str(exc)
        st.session_state.models_initialized = True
        if notify:
            st.session_state.model_notice = "Could not refresh the installed model list."
        _reconcile_selected_model(client)
        return

    st.session_state.available_models = [item["name"] for item in details]
    st.session_state.model_details = {item["name"]: item for item in details}
    st.session_state.model_list_error = None
    st.session_state.models_initialized = True
    _reconcile_selected_model(client)
    _apply_selected_model()


def _refresh_models_callback() -> None:
    """Button callback: bypass caches and discover models again."""
    st.session_state.model_test_result = None
    _load_models(force_refresh=True, notify=True)


def _test_selected_model(model: str) -> None:
    """Send one short prompt to the selected model and record the outcome."""
    client = _get_ollama_client()
    client.set_model(model)
    started = time.perf_counter()
    try:
        with st.spinner(f"Testing `{model}`…"):
            response = client.generate(
                prompt="Reply with exactly one word: ready",
                system="You are a connectivity test. Keep the reply to one word.",
                model=model,
                temperature=0.0,
            )
    except Exception as exc:
        st.session_state.model_test_result = {
            "ok": False,
            "model": model,
            "message": str(exc),
            "elapsed": time.perf_counter() - started,
        }
        return

    st.session_state.model_test_result = {
        "ok": True,
        "model": model,
        "response": (response or "").strip(),
        "elapsed": time.perf_counter() - started,
    }


def _render_model_test_result() -> None:
    result = st.session_state.get("model_test_result")
    if not result:
        return

    elapsed = result.get("elapsed", 0.0)
    if result.get("ok"):
        st.sidebar.success(
            f"`{result['model']}` responded in {elapsed:.2f}s."
        )
        response = result.get("response") or "(empty response)"
        st.sidebar.caption(f"Test response: {response[:300]}")
    else:
        st.sidebar.error(
            f"Model test failed for `{result['model']}` after {elapsed:.2f}s: "
            f"{result.get('message', 'unknown error')}"
        )


def _render_llm_configuration():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 LLM Model Configuration")

    # Startup discovery happens once; refreshes are explicit.
    if not st.session_state.get("models_initialized"):
        _load_models(force_refresh=False)

    client = _get_ollama_client()
    is_up, msg = client.check_availability()
    st.session_state.ollama_status = (is_up, msg)

    st.sidebar.button(
        "🔄 Refresh installed models",
        key="refresh_models",
        on_click=_refresh_models_callback,
        width="stretch",
    )

    if is_up:
        st.sidebar.markdown(
            '<span class="badge-ok">● Ollama connected</span>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<span class="badge-err">✗ Ollama not detected</span>',
            unsafe_allow_html=True,
        )
        st.sidebar.caption("Start Ollama with `ollama serve`, then click Refresh.")
        st.sidebar.caption("Navigation will use deterministic fallback mode.")

    notice = st.session_state.pop("model_notice", None)
    if notice:
        st.sidebar.info(notice)

    names = list(st.session_state.get("available_models") or [])
    list_error = st.session_state.get("model_list_error")

    if list_error:
        st.sidebar.error(
            "Could not read installed models. Ensure Ollama is running and click Refresh."
        )

    if names:
        selected = st.sidebar.selectbox(
            "Select model",
            options=names,
            key="selected_model",
            help="Installed models are read from Ollama's /api/tags endpoint.",
        )
        _apply_selected_model()

        st.sidebar.caption(f"**Model used for next navigation:** `{selected}`")

        detail = st.session_state.model_details.get(selected, {})
        meta = []
        size_label = _format_model_size(detail.get("size"))
        if size_label:
            meta.append(f"Size on disk: {size_label}")
        if detail.get("parameter_size"):
            meta.append(f"Parameters: {detail['parameter_size']}")
        if detail.get("quantization_level"):
            meta.append(f"Quantization: {detail['quantization_level']}")
        if meta:
            st.sidebar.caption(" · ".join(meta))

        st.sidebar.caption(
            "Larger models may use more system RAM and run slower on machines with limited VRAM."
        )

        if st.sidebar.button(
            "🧪 Test Selected Model",
            key="test_selected_model",
            width="stretch",
        ):
            _test_selected_model(selected)

        _render_model_test_result()
    elif not list_error:
        st.sidebar.warning(
            "No Ollama models are installed.\n\n"
            "Install one with `ollama pull qwen3.5:4b` and click "
            "**Refresh installed models**. MapMind does not download models automatically."
        )


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
    # 1. Load the original image. The parser records both source and working
    #    dimensions so the UI never mixes coordinate spaces.
    orig_img = load_floorplan(image_path)

    # 2. Run full CV + graph pipeline. Passing output_dir keeps every artifact
    #    (floorplan.json + debug images) inside this upload's isolated workdir.
    fp = parse_floorplan(image_path, output_dir=workdir)

    # 3. Build and persist the graph in the same workdir.
    builder = NavigationGraphBuilder(fp)
    G = builder.graph
    save_navigation_graph_json(G, workdir / "navigation_graph.json")

    # 4. Convert detection geometry back to source coordinates before drawing
    #    on the original image. The working-coordinate FloorPlan is retained for
    #    tables/debugging and existing API compatibility.
    fp_source = scale_floorplan_to_source(fp)
    ann_img = visualize_floorplan(fp_source, orig_img)

    # 5. Store in session state
    st.session_state.floorplan = fp
    st.session_state.floorplan_source = fp_source
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
        if st.sidebar.button(
            "▶ Load Demo Floor Plan", key="load_demo", width="stretch"
        ):
            _clear_floorplan_state()
            tmpdir = get_session_tmpdir() / "demo"
            tmpdir.mkdir(parents=True, exist_ok=True)
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
                    _clear_floorplan_state()
                    st.session_state.upload_hash = None
                    st.sidebar.error(f"Failed to load demo: {exc}")

    else:  # Upload
        uploaded = st.sidebar.file_uploader(
            "Upload floor plan image",
            type=ALLOWED_TYPES,
            help=f"PNG, JPG, or JPEG · Max {MAX_UPLOAD_MB} MB",
        )
        if uploaded is not None:
            raw_bytes = uploaded.getvalue()

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

            # Only process a file once. Marking the hash before processing
            # means a failed upload is not retried on every Streamlit rerun.
            if _begin_upload(st.session_state, h):
                tmpdir = get_upload_workdir(get_session_tmpdir(), h)

                # Save raw upload to workdir
                ext = Path(uploaded.name).suffix or ".png"
                img_path = tmpdir / f"upload{ext}"
                img_path.write_bytes(raw_bytes)

                with st.spinner("Running CV pipeline on uploaded floor plan…"):
                    try:
                        _process_floorplan(img_path, tmpdir)
                        st.session_state.floor_source = "upload"
                        st.session_state.workdir = tmpdir
                        st.sidebar.success("Floor plan processed successfully.")
                    except Exception as exc:
                        log.exception("Upload processing failed")
                        _clear_floorplan_state()
                        st.session_state.upload_hash = h
                        st.sidebar.error(f"Processing failed: {exc}")

            # Render the retry control outside the one-shot processing block,
            # so it remains visible after a failure without auto-retrying on
            # every rerun. The callback resets the hash before the next run.
            if (
                st.session_state.get("upload_hash") == h
                and st.session_state.get("floorplan") is None
            ):
                st.sidebar.button(
                    "Retry processing",
                    key="retry_upload",
                    on_click=_retry_upload,
                    width="stretch",
                )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Processing Info")
    if st.session_state.floorplan:
        fp = st.session_state.floorplan
        source_size = (
            f"{fp.source_width} × {fp.source_height}"
            if fp.source_width and fp.source_height
            else f"{fp.image_width} × {fp.image_height}"
        )
        st.sidebar.caption(
            f"Source image: {source_size} px\n"
            f"Processed: {fp.image_width} × {fp.image_height} px\n"
            f"Rooms: {len(fp.rooms)} | Corridors: {len(fp.corridors)}\n"
            f"Doors: {len(fp.doors)} | Walls: {len(fp.walls)}"
        )
    else:
        st.sidebar.caption("No floor plan loaded yet.")

    _render_llm_configuration()


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

    graph = st.session_state.graph
    isolated = list(graph.graph.get("isolated_nodes", [])) if graph is not None else []
    if isolated:
        st.warning(
            "No door was detected for these regions, so they cannot be used as "
            f"navigation endpoints yet: {', '.join(isolated)}"
        )

    # -----------------------------------------------------------------------
    # Floor plan images: original + annotated
    # -----------------------------------------------------------------------
    st.markdown('<div class="section-heading">Floor Plan Visualization</div>', unsafe_allow_html=True)
    c_orig, c_ann = st.columns(2)
    with c_orig:
        st.markdown("**Original Floor Plan**")
        if st.session_state.orig_img_bytes:
            st.image(st.session_state.orig_img_bytes, width="stretch")
    with c_ann:
        st.markdown("**Annotated Detections**")
        if st.session_state.annotated_img_bytes:
            st.image(st.session_state.annotated_img_bytes, width="stretch")
        st.caption(
            "🟩 Rooms&nbsp;&nbsp; 🟨 Corridors&nbsp;&nbsp; 🟣 Doors (D#)&nbsp;&nbsp; 🔴 Walls"
        )

    # -----------------------------------------------------------------------
    # Debug images expandable section
    # -----------------------------------------------------------------------
    workdir: Optional[Path] = st.session_state.workdir
    if workdir:
        debug_files = {
            "Source Overlay": workdir / "source_overlay_debug.png",
            "Regions": workdir / "segmentation_masks_debug.png",
            "Rooms": workdir / "rooms_debug.png",
            "Doors": workdir / "doors_debug.png",
            "Door Candidates": workdir / "door_candidates_debug.png",
            "Corridors": workdir / "corridors_debug.png",
            "Walls": workdir / "walls_debug.png",
            "Wall Candidates": workdir / "wall_candidates_debug.png",
            "Wall Mask": workdir / "walls_bin_debug.png",
            "Closed Walls": workdir / "closed_walls_debug.png",
        }
        available_debug = {k: p for k, p in debug_files.items() if p.exists()}
        if available_debug:
            with st.expander("Debug Visualizations", expanded=False):
                debug_tabs = st.tabs(list(available_debug.keys()))
                for tab, path in zip(debug_tabs, available_debug.values()):
                    with tab:
                        st.image(str(path), width="stretch")

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
                width="stretch",
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("Node ID"),
                    "Type": st.column_config.TextColumn("Type"),
                    "Area (px²)": st.column_config.NumberColumn("Area (px²)", format="%d"),
                },
            )
            st.caption(
                "⚠️ Room IDs are assigned automatically by the CV pipeline (Room_1, Room_2 …). "
                "Printed names require OCR; demo aliases such as Reception/Room 101 apply only to the built-in demo."
            )
        else:
            st.warning("No rooms or corridors detected.")

    with tab_doors:
        door_rows = doors_to_table(fp)
        if door_rows:
            st.dataframe(door_rows, width="stretch", hide_index=True)
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
            st.dataframe(conn_rows, width="stretch", hide_index=True)
        else:
            st.warning("No connections detected. Navigation may not be available.")


# ===========================================================================
# NAVIGATION PANEL
# ===========================================================================

def _navigation_examples(fp, is_demo: bool):
    """Build example queries from the loaded plan instead of demo-only names."""
    if is_demo:
        return DEMO_QUERIES
    room_names = [room.name for room in fp.rooms]
    corridor_names = [corridor.name for corridor in fp.corridors]
    if len(room_names) < 2:
        return DEMO_QUERIES
    first, second = room_names[0], room_names[1]
    third = room_names[2] if len(room_names) > 2 else first
    examples = [
        f"How do I get from {first} to {second}?",
        f"Navigate from {second} to {third}.",
        f"Where is {second}?",
    ]
    if corridor_names:
        examples.append(f"How do I reach the corridor from {first}?")
    else:
        examples.append(f"Find a route from {third} to {first}.")
    return examples


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
    examples = _navigation_examples(
        fp, st.session_state.get("floor_source") == "demo"
    )
    st.markdown("**Enter a navigation query:**")
    query_input = st.text_input(
        label="Navigation query",
        placeholder=f'e.g. "{examples[0]}"',
        label_visibility="collapsed",
        key="nav_query_input",
    )

    st.markdown("**Quick examples:**")
    eq_cols = st.columns(len(examples))
    for idx, example in enumerate(examples):
        eq_cols[idx].button(
            f'"{example}"',
            key=f"eq_{idx}",
            on_click=_set_nav_query,
            args=(example,),
            width="stretch",
        )

    nav_submit = st.button("🧭 Navigate", type="primary", width="content")

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

    # Clear any previous result/overlay so a failed attempt cannot display a
    # stale route from an earlier query.
    st.session_state.nav_result = None
    st.session_state.route_img_bytes = None

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
                    route_fp = st.session_state.get("floorplan_source") or fp
                    overlay = draw_route_overlay(ann_img, route_fp, route)
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

    # ---- Route summary card (all dynamic text is HTML-escaped) ----
    path_arrow = " → ".join(html.escape(str(p)) for p in path) if path else "—"
    doors_str = " → ".join(html.escape(str(d)) for d in doors) if doors else "None"
    method_str = html.escape(str(method))
    instructions_label = (
        f"LLM ({method_str})" if is_llm else "Deterministic fallback"
    )

    st.markdown(
        f"""
<div class="route-card">
  <div class="path-row">🗺️ {path_arrow}</div>
  <div class="meta">🚪 Doors: {doors_str}</div>
  <div class="meta">📏 Route cost: <strong>{float(dist):.1f} pixels</strong> · {int(hops)} hop(s)</div>
  <div class="meta">🤖 Instructions: <strong>{instructions_label}</strong></div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not is_llm and method and "ollama" not in method.lower():
        st.caption("ℹ️ Deterministic instructions shown — Ollama unavailable or generation timed out.")

    # ---- Navigation instructions ----
    st.markdown("**Navigation Instructions**")
    explanation = html.escape(str(res.get("explanation", "")))
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
            st.image(st.session_state.route_img_bytes, width="stretch")
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
            st.pyplot(fig, width="stretch")
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
        st.pyplot(fig, width="stretch")
        plt_mod.close(fig)


# ===========================================================================
# MAIN LAYOUT
# ===========================================================================

def main():
    _init_session()

    # Sidebar
    render_sidebar()

    # Header
    selected_model = st.session_state.get("selected_model")
    model_label = html.escape(selected_model) if selected_model else "Ollama"
    st.markdown(
        f"""
<div class="mapmind-header">
  <h1>🗺️ MapMind</h1>
  <p>
    Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local LLMs<br>
    <small>Phase 1–5 · OpenCV · NetworkX · A* Pathfinding · Ollama (<code>{model_label}</code>)</small>
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
