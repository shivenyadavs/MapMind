# MapMind

## Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local LLMs

MapMind is an end-to-end research prototype combining classical Computer Vision (CV), topological graph representation, A* search pathfinding, and local Large Language Models (LLM via Ollama) for indoor floor-plan navigation — all running locally without cloud APIs.

---

## Project Status

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | OpenCV image preprocessing pipeline | ✅ Complete |
| **Phase 2** | Room, door, corridor and wall detection | ✅ Complete |
| **Phase 3** | Structured FloorPlan JSON + NetworkX navigation graph | ✅ Complete |
| **Phase 4** | A* pathfinding + local Ollama LLM integration | ✅ Complete |
| **Phase 5** | Streamlit interactive web application | ✅ Complete |

---

## Architecture

```
Floor Plan Image
      │
      ▼  [Phase 1-2] OpenCV CV Pipeline
parse_floorplan()  →  FloorPlan (Pydantic model)
      │
      ▼  [Phase 3] Graph Construction
NavigationGraphBuilder  →  NetworkX Graph (rooms/corridors → edges via doors)
      │
      ▼  [Phase 4] Navigation
User Query → QueryParser → A* Pathfinder → OllamaClient → Instructions
      │
      ▼  [Phase 5] Streamlit UI
frontend/app.py  →  Interactive web app at http://localhost:8501
```

### CV Configuration

The parser is ratio-based and configurable:

```python
from cv.floorplan_parser import parse_floorplan
from cv.pipeline_config import CVConfig

fp = parse_floorplan(
    "plan.png",
    output_dir="data/processed",
    config=CVConfig(max_dimension=1200, debug=False),
)
print(fp.diagnostics)
```

Detections are stored in working-resolution coordinates (`fp.image_width/height`).
Original-image dimensions are in `fp.source_width/source_height`; use
`cv.coordinates.scale_floorplan_to_source(fp)` before drawing on the original
upload. With `debug=True`, debug images are written to `output_dir`.

By default the parser suppresses isolated printed labels (which otherwise
binarise as short walls) and evaluates several door-closing gap sizes, choosing
the one that yields the most valid rooms/corridors. This keeps large apartment
rooms and densely packed mall units on the same defaults. Set
`CVConfig(adaptive_segmentation=False, segmentation_gap_ratio=...)` to force a
single gap for experiments.

---

## Installation & Setup

### 1. Clone & Install

```bash
git clone https://github.com/your-username/mapmind.git
cd mapmind

python -m venv venv
venv\Scripts\activate      # Windows PowerShell

pip install -r requirements.txt
```

### 2. Local Ollama Setup

MapMind runs fully offline. Ollama is only required for LLM-enhanced navigation instructions; A* pathfinding always works without it.

```bash
# Install Ollama from https://ollama.com/download
# Then start the server:
ollama serve

# Pull the configured model:
ollama pull qwen3.5:4b
```

Configure via `.env` (copy from `.env.example`):

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
OLLAMA_TIMEOUT=30
```

`OLLAMA_MODEL` sets the initial default. In the app sidebar, **LLM Model Configuration** lists every model installed in Ollama; choose any of them at runtime without restarting. The selection applies to subsequent navigation requests and the **Test Selected Model** button.

---

## Launching the Web Application (Phase 5)

```bash
streamlit run frontend/app.py
```

Opens at **http://localhost:8501**.

### Using the App

**Load the Built-in Demo:**
1. Sidebar → Built-in Demo → click **▶ Load Demo Floor Plan**
2. CV pipeline runs; switch to **🔍 Detection** tab for results

**Upload Your Own Floor Plan:**
1. Sidebar → Upload Your Own → drag and drop PNG/JPG/JPEG (max 20 MB)
2. Each upload is processed in an isolated directory (previous results not affected)

**Run a Navigation Query:**
1. Switch to **🧭 Navigation** tab
2. Type a query or click an example:
   - *"How do I get from Reception to Room 104?"*
   - *"Navigate from Room 101 to Room 102."*
3. Click **🧭 Navigate** — results show path, doors, cost, and LLM instructions

**Inspect the Navigation Graph:**
- Switch to **📊 Graph** tab for the topological graph diagram and node/edge details

---

## CLI Navigation (Phase 4)

```bash
# Full benchmark demo
python main.py

# Single query
python main.py --query "How do I get from Reception to Room 104?"

# Direct routing
python main.py --source Room_1 --destination Room_5

# Interactive CLI
python main.py --interactive

# Without Ollama (deterministic fallback)
python main.py --query "from Reception to Room 104" --no-llm
```

---

## Running Tests

```bash
pytest -q
```

**117 tests pass** across all phases:

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_preprocessing.py` | 4 | Phase 1 image processing |
| `tests/test_floorplan_parser.py` | 5 | Phase 2 CV parser |
| `tests/test_graph.py` | 11 | Phase 3 graph topology |
| `tests/test_phase4.py` | 18 | Phase 4 A*, LLM client, query parser |
| `tests/test_phase5.py` | 31 | Phase 5 UI helpers, fallback, isolation |
| `tests/test_bugfixes.py` | 21 | Regression tests for the reliability fixes |
| `tests/test_model_selector.py` | 13 | Model discovery, selection, switching, fallback |
| `tests/test_cv_improvements.py` | 12 | Coordinates, CV config, OCR fallback, graph validation |

---

## Project Structure

```
mapmind/
├── cv/                       # Phases 1-2: OpenCV pipeline
│   ├── preprocessing.py      # Image loading, denoising, synthetic floor plan
│   ├── floorplan_parser.py   # Detection: rooms, doors, corridors, walls, connections
│   ├── pipeline_config.py    # Ratio-based CV thresholds
│   ├── coordinates.py        # Working ↔ source coordinate conversion
│   ├── ocr.py                # Optional printed-label OCR
│   ├── visualization.py      # Annotated floor-plan rendering
│   └── models.py             # Pydantic data models
├── graph/                    # Phase 3: Navigation graph
│   ├── graph_builder.py      # NetworkX graph construction from FloorPlan
│   ├── graph_visualizer.py   # Matplotlib spatial + topological dual-panel plot
│   └── pathfinder.py         # A* search with Euclidean heuristic
├── llm/                      # Phase 4: LLM integration
│   ├── ollama_client.py      # Local Ollama HTTP client (no cloud APIs)
│   ├── query_parser.py       # NL query → graph node resolution (regex + LLM fallback)
│   └── response_generator.py # Route explanation (LLM + deterministic fallback)
├── frontend/                 # Phase 5: Streamlit application
│   ├── app.py                # Main Streamlit application
│   └── ui_helpers.py         # Stateless helper functions (image, graph, tables)
├── tests/                    # All test suites (117 tests)
├── data/
│   ├── raw/                  # Sample floor plan images
│   └── processed/            # Generated artifacts (JSON, PNG)
├── navigation_service.py     # End-to-end navigation orchestration layer
├── main.py                   # CLI entry point
├── run_phase2.py             # Phase 2 runner
├── run_phase3.py             # Phase 3 runner
├── requirements.txt
├── .env.example
└── README.md
```

---

## Graceful Degradation

All non-LLM features work without an Ollama server:

| Feature | Without Ollama |
|---------|----------------|
| Floor plan CV detection | ✅ Full |
| Navigation graph construction | ✅ Full |
| A* pathfinding & route cost | ✅ Full |
| Query parsing (aliases) | ✅ Full |
| Navigation instructions | ✅ Deterministic structured text |
| LLM-enhanced instructions | ❌ Requires Ollama + model |

---

## Known Limitations

- **Pixel-Based Distance:** Route costs are in image pixels. No real-world metric scale (metres) is available without calibration metadata.
- **Undirected Doorways:** All detected doors assume two-way transit.
- **Optional OCR:** Room IDs are auto-assigned by default. If `pytesseract` and the Tesseract executable are installed, printed labels are associated with segmented regions; unknown text is kept as its printed name without inventing a category. Without OCR, mall stores/restaurants remain `Room_N`; demo aliases (Reception/Room 101) apply only to the bundled five-room sample and are not mapped onto uploads. OCR has not been validated against a real mall plan in this repository.
- **CV Accuracy:** Detection quality depends on floor-plan contrast and wall clarity. Very low-contrast or complex images may yield fewer detected regions. Mall plans can still merge wide/L-shaped halls into room regions, and some small store doors may be missed, leaving isolated nodes. No annotated mall benchmark or ground truth is included, so mall-specific precision/recall is not measured.
- **LLM Grounding:** LLM explanations are rejected when they mention room/door IDs outside the computed route or invent left/right turns; the deterministic explanation is shown instead.
- **Working Resolution:** Detection runs at a configurable working resolution (default longest side 1200 px). Detections are stored in working coordinates and scaled back to source coordinates for overlays; very small doors may be lost during downscaling.
- **Single Floor Only:** Multi-storey plans are not supported.
- **Upload Persistence:** Uploaded floor-plan processing results are stored in the server's temp directory and are not persisted across server restarts.
