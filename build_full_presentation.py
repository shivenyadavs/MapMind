import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333) # 16:9 widescreen
prs.slide_height = Inches(7.5)

# Color Palette
DARK_NAVY = RGBColor(16, 44, 87)
ACCENT_BLUE = RGBColor(53, 114, 239)
BODY_GRAY = RGBColor(40, 40, 40)
LIGHT_BG = RGBColor(245, 247, 250)

def set_slide_background(slide, color):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_header(slide, title_text, category="MAPMIND: RESEARCH DEFENSE & TECHNICAL PRESENTATION"):
    # Header category
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.4))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = category.upper()
    p_cat.font.name = "Arial"
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = ACCENT_BLUE

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.8))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title_text
    p_t.font.name = "Arial"
    p_t.font.size = Pt(24)
    p_t.font.bold = True
    p_t.font.color.rgb = DARK_NAVY

def add_slide_with_notes(prs, title, bullets, notes_text, category=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6]) # blank layout
    if category:
        add_header(slide, title, category)
    else:
        add_header(slide, title)
    
    # Content box
    content_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0))
    tf = content_box.text_frame
    tf.word_wrap = True
    
    for i, bullet in enumerate(bullets):
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        p.text = bullet
        p.font.name = "Calibri"
        p.font.size = Pt(18)
        p.font.color.rgb = BODY_GRAY
        p.space_after = Pt(14)
        p.level = 0
        
    # Add Speaker Notes
    notes_slide = slide.notes_slide
    text_frame = notes_slide.notes_text_frame
    text_frame.text = notes_text
    return slide

# =========================================================================
# SLIDE 1: Title Slide
# =========================================================================
slide1 = prs.slides.add_slide(prs.slide_layouts[6])
set_slide_background(slide1, LIGHT_BG)

title_box = slide1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.3), Inches(2.2))
tf1 = title_box.text_frame
tf1.word_wrap = True
p1 = tf1.paragraphs[0]
p1.text = "MapMind: Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local LLMs"
p1.font.name = "Arial"
p1.font.size = Pt(32)
p1.font.bold = True
p1.font.color.rgb = DARK_NAVY
p1.space_after = Pt(12)

sub_box = slide1.shapes.add_textbox(Inches(1.0), Inches(4.2), Inches(11.3), Inches(1.5))
tf_sub = sub_box.text_frame
tf_sub.word_wrap = True
p_sub = tf_sub.paragraphs[0]
p_sub.text = "A Fully Offline, Edge-Deployable Classical CV & Topological Graph Framework with Grounded LLMs\n117 / 117 Verified Tests | CPU-Only Execution | Evaluated on Real Commercial Mall Plans"
p_sub.font.name = "Calibri"
p_sub.font.size = Pt(18)
p_sub.font.color.rgb = ACCENT_BLUE

meta_box = slide1.shapes.add_textbox(Inches(1.0), Inches(5.8), Inches(11.3), Inches(0.8))
tf_meta = meta_box.text_frame
p_meta = tf_meta.paragraphs[0]
p_meta.text = "Author: [Author Name] | Department of Computer Science & Engineering | [Institution Name]"
p_meta.font.name = "Calibri"
p_meta.font.size = Pt(14)
p_meta.font.italic = True
p_meta.font.color.rgb = BODY_GRAY

slide1.notes_slide.notes_text_frame.text = (
    "SPEAKER NOTES (Slide 1 - Title):\n"
    "Say: 'Good morning/afternoon, respected examiners and committee members. Today I am presenting MapMind: "
    "Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local Large Language Models. "
    "MapMind is a complete, fully offline, edge-deployable indoor navigation platform that transforms unannotated architectural "
    "floor plans into structured, door-aware topological navigation graphs, enabling conversational wayfinding without cloud APIs, "
    "without GPU hardware, and without manual map tagging.'\n"
    "Time: 30 seconds.\n"
    "Transition: 'Let us begin by examining the core problem that makes indoor navigation so challenging.'"
)

# =========================================================================
# SLIDE 2: Problem Statement & Motivation
# =========================================================================
add_slide_with_notes(
    prs,
    "Problem Statement: The Indoor Navigation Void",
    [
        "• GPS Line-of-Sight Blackout: Satellite signals are completely blocked by concrete, masonry, and steel roofs.",
        "• Spatial Disorientation in Complex Facilities: Modern hospitals, airports, and malls create visitor friction.",
        "• Exorbitant Physical Beacon Infrastructure: Wi-Fi/BLE beacons demand high capital cost and continuous calibration.",
        "• The Raster Floor-Plan Reality: Building maps exist almost exclusively as unstructured, unannotated 2D raster images.",
        "• Data Privacy & Cloud Vulnerabilities: Streaming proprietary building floor plans or patient/visitor queries to cloud APIs violates strict institutional privacy."
    ],
    "SPEAKER NOTES (Slide 2 - Problem Statement):\n"
    "Say: 'While outdoor navigation is solved by GPS, indoor navigation remains an infrastructure void. Once a user steps inside "
    "a hospital or large shopping mall, GPS signals drop to zero. The current industry standard requires either installing hundreds "
    "of physical Bluetooth beacons—which are expensive and fragile—or forcing users to decipher static, unannotated raster images. "
    "Furthermore, commercial facilities and healthcare institutions cannot upload proprietary building layouts to external cloud AI "
    "services due to privacy and security compliance.'\n"
    "Key Point: Emphasize the absence of GPS and the prevalence of unannotated floor-plan images.\n"
    "Time: 1 minute.\n"
    "Transition: 'This brings us to the research gap and our core project objectives.'"
)

# =========================================================================
# SLIDE 3: Research Gap & Objectives
# =========================================================================
add_slide_with_notes(
    prs,
    "Research Gap & Project Objectives",
    [
        "• The Academic Divide: Prior works either rely on data-hungry deep neural networks (e.g. CubiCasa5K) or stop at raw CAD line extraction without topological path planning.",
        "• The Wall-Clipping Routing Defect: Existing academic floor-plan parsers connect room centroids with straight lines that cut through thick concrete walls.",
        "• Core Objective 1: Deliver an end-to-end, CPU-only classical CV pipeline from raw pixels to semantic architectural primitives.",
        "• Core Objective 2: Build a door-center-aware topological graph engine that guarantees physically navigable trajectories.",
        "• Core Objective 3: Integrate local, offline LLMs (via Ollama) with deterministic grounding verification to completely eliminate spatial hallucinations."
    ],
    "SPEAKER NOTES (Slide 3 - Research Gap & Objectives):\n"
    "Say: 'Existing research has two major shortcomings: deep learning vectorizers require thousands of annotated floor plans and server GPUs, "
    "while basic topological parsers connect room centers directly, producing routes that clip straight through solid walls. "
    "MapMind bridges this gap with three concrete objectives: first, a CPU-based classical CV parser; second, a door-center-aware graph engine; "
    "and third, an offline local LLM interface with strict grounding guardrails that guarantee zero spatial hallucinations.'\n"
    "Time: 1 minute.\n"
    "Transition: 'Let us briefly place this in the context of existing literature.'"
)

# =========================================================================
# SLIDE 4: Related Work
# =========================================================================
add_slide_with_notes(
    prs,
    "Related Work & Prior Benchmarks",
    [
        "• Indoor Positioning Surveys: Liu et al. (IEEE Trans. 2007) and Zafari et al. (IEEE ComSurv 2019) catalog radio/beacon methods.",
        "• Floor Plan Datasets & Neural Vectorizers: CubiCasa5K (Kalervo et al., SCIA 2019) and Raster-to-Vector (Liu et al., ICCV 2017) demonstrated CNN/GNN floor plan parsing.",
        "• Classical Architectural Extraction: Macé et al. (DAS 2010) and Afzal et al. (ICRA 2014) pioneered heuristic room extraction and topological mapping.",
        "• Optimal Heuristic Pathfinding: A* Search Algorithm (Hart, Nilsson, Raphael, IEEE SSC 1968) using admissible Euclidean metrics.",
        "• Edge LLM Deployment: Ollama runtime (2024) enabling local inference with Microsoft Phi, Meta Llama-3, and Mistral."
    ],
    "SPEAKER NOTES (Slide 4 - Related Work):\n"
    "Say: 'Our work builds on established foundations across four domains: the indoor positioning taxonomies of Liu and Zafari; "
    "the floor plan vectorization benchmarks of CubiCasa5K and Raster-to-Vector; the classical topological mapping work of Macé and Afzal; "
    "and the foundational A* search algorithm of Hart et al. Unlike deep learning approaches that require massive training data, "
    "MapMind achieves deterministic vectorization using classical CV and connects it directly to local LLMs.'\n"
    "Time: 1 minute.\n"
    "Transition: 'Here is how the four layers of MapMind fit together in our system architecture.'"
)

# =========================================================================
# SLIDE 5: System Architecture
# =========================================================================
add_slide_with_notes(
    prs,
    "MapMind End-to-End System Architecture",
    [
        "• Layer 1 - Streamlit UI: User uploads raster floor plan, views toggleable detection layers, interacts via natural language, and receives visual route overlays.",
        "• Layer 2 - Classical CV Pipeline: Standardizes resolution (1200 px max), performs color separation, typographic text suppression, adaptive gap closing, and region segmentation.",
        "• Layer 3 - Topological Navigation Graph: NetworkX undirected graph where nodes = rooms/corridors, edges = doors, and weights = room-centroid-to-door distances.",
        "• Layer 4 - Grounded Local LLM Engine: Regex query parser extracts intent and slots; local Ollama LLM generates natural explanations; deterministic verifier rejects hallucinations.",
        "• 100% Edge Execution: Zero network packets, zero cloud APIs, zero external data leakage."
    ],
    "SPEAKER NOTES (Slide 5 - System Architecture):\n"
    "Say: 'The MapMind architecture is structured into four tightly coordinated layers: the Streamlit user interface; "
    "the classical computer vision engine implemented in OpenCV; the topological graph and pathfinding engine in NetworkX; "
    "and the grounded local LLM module in Ollama. Crucially, all four layers execute completely on the local host CPU. "
    "No floor plans or user queries are ever transmitted across the network, guaranteeing total privacy.'\n"
    "Time: 1 minute.\n"
    "Transition: 'Let us examine the algorithmic steps of our computer vision pipeline.'"
)

# =========================================================================
# SLIDE 6: Computer Vision Pipeline
# =========================================================================
add_slide_with_notes(
    prs,
    "Computer Vision & Structural Feature Extraction",
    [
        "• Achromatic Separation: Isolate dark masonry walls (delta <= 28, V <= 175) from colored architectural markers.",
        "• Typographic Text Suppression: Purges printed room labels (STORE, CAFE) using bounding-box heuristics, preventing rooms from shattering into micro-fragments.",
        "• Candidate-Driven Adaptive Closing: Evaluates 6 gap ratios (0.03 to 0.09) and selects gamma* that maximizes valid room recovery.",
        "• Hough Line Detection & Segment Merging: Merges collinear fragments (Delta theta <= 7.5 deg, dist <= 0.012) with 52% wall mass support verification.",
        "• Connected-Component Inversion: Inverts closed walls to extract free space; classifies Corridors (aspect >= 4.0, solidity >= 0.20) and Rooms.",
        "• Dual-Source Door Detection: Pairs chromatic symbol masks with free-space boundary region gaps; resolves orientation via orthogonal ray probing."
    ],
    "SPEAKER NOTES (Slide 6 - CV Pipeline):\n"
    "Say: 'Our computer vision pipeline solves the core challenges of floor plan parsing without neural networks. "
    "First, we separate dark walls from colored architectural markings. Second, our typographic text suppression algorithm "
    "removes printed labels like STORE or ROOM 101, which otherwise fracture rooms into dozens of tiny pieces. "
    "Third, adaptive gap closing tests six morphological kernel sizes to seal wall openings without bridging doorways. "
    "Fourth, Hough lines are merged into clean structural walls. Finally, connected components separate rooms from corridors, "
    "and our orthogonal ray probe links doors directly to their parent rooms.'\n"
    "Time: 1.5 minutes.\n"
    "Transition: 'Once architectural features are extracted, how do we construct the navigation graph?'"
)

# =========================================================================
# SLIDE 7: Location Inventory & Navigation Graph
# =========================================================================
add_slide_with_notes(
    prs,
    "Location Inventory & Topological Graph Synthesis",
    [
        "• Node Synthesis: Every detected room (Room_1...Room_N) and corridor (Corridor_1) becomes a graph vertex with (x, y) centroid, bounding box, and area.",
        "• Door-Center Edge Weighting: Traversal weight omega(u, v) = ||c(u) - c(d)||_2 + ||c(d) - c(v)||_2, accurately modeling walking distance through the door threshold.",
        "• Isolated Node Detection: NetworkX connectivity checks identify disconnected regions (e.g. Room_26 in mall plan), warning users in real time.",
        "• Door-Center-Aware A* Pathfinding: Uses Euclidean distance heuristic h(u, t) = ||c(u) - c(t)||_2; strictly admissible and consistent.",
        "• Wall-Avoidant Trajectory Rendering: Overlays multi-segment paths (room center -> door threshold -> room center), completely eliminating wall-clipping artifacts."
    ],
    "SPEAKER NOTES (Slide 7 - Navigation Graph):\n"
    "Say: 'From the extracted inventory, NetworkX synthesizes an undirected topological graph. Nodes are room centroids, "
    "and edges represent verified doors. Unlike naive graphs that use hop counts or direct centroid lines, MapMind calculates "
    "the exact walking distance: from room centroid, through the physical door threshold, to the next room centroid. "
    "Our A* pathfinder uses an admissible Euclidean heuristic that guarantees shortest paths. When we draw the route overlay, "
    "it visually threads through the door opening rather than cutting across solid concrete walls.'\n"
    "Time: 1 minute.\n"
    "Transition: 'Now, how does a user interact with this graph using natural language?'"
)

# =========================================================================
# SLIDE 8: NLQ & Local LLM Integration
# =========================================================================
add_slide_with_notes(
    prs,
    "Natural-Language Query & Grounded Local LLMs",
    [
        "• Canonical Intent Classification: High-speed regex parser classifies queries into navigate(s, d), where_is(target), how_many(type), or clarification.",
        "• Entity Slot Filling: Robust regex normalizes linguistic variations ('room 1', 'Room_1', 'room101') against active floor plan inventory.",
        "• Offline Local LLM Inference: Invokes local quantized models (Phi-2, Llama-3-8B) via Ollama, passing verified route context in system prompts.",
        "• The Grounding Rejection Guardrail: Generated text is programmatically audited; if the LLM invents nonexistent room IDs or hallucinated turn instructions, it is instantly rejected.",
        "• Deterministic Rule-Based Fallback: Seamlessly substitutes verified graph explanations, ensuring 100% factual accuracy."
    ],
    "SPEAKER NOTES (Slide 8 - NLQ & Local LLM):\n"
    "Say: 'For conversational interaction, user queries are first evaluated by our fast query parser to identify the intent and extract room entities. "
    "If conversational explanations are requested, we invoke a local LLM such as Microsoft Phi or Llama-3 through Ollama. "
    "However, to solve the well-known LLM hallucination problem, we built a strict Grounding Rejection layer: if the LLM mentions any room "
    "not in the computed route or invents unverified turn instructions, the output is discarded and replaced with our deterministic rule-based explanation. "
    "The user always receives 100% verified directions.'\n"
    "Time: 1 minute.\n"
    "Transition: 'Let us look at our experimental setup and evaluation environments.'"
)

# =========================================================================
# SLIDE 9: Experimental Setup
# =========================================================================
add_slide_with_notes(
    prs,
    "Experimental Setup & Benchmark Environments",
    [
        "• Software Environment: Python 3.12, OpenCV 4.x, NetworkX 3.3, ReportLab 5.1, Streamlit 1.38, Ollama edge runtime.",
        "• Hardware Invariant: Standard commodity Intel CPU laptop; zero GPU acceleration required.",
        "• Benchmark 1 - Academic Baseline: 5 rooms, 1 corridor, 6 doors, 16 walls (600 x 400 px).",
        "• Benchmark 2 - Residential Apartment: 6 rooms, 1 corridor, 6 doors, 60 walls (800 x 600 px).",
        "• Benchmark 3 - Real Commercial Mall: 33 retail/dining units, 1 corridor, 38 doors, 118 walls (650 x 904 px).",
        "• Execution Latency: Complete parsing and graph construction executed in ~2.0 seconds on CPU."
    ],
    "SPEAKER NOTES (Slide 9 - Experimental Setup):\n"
    "Say: 'We rigorously tested MapMind across three distinct architectural layouts: a 5-room academic baseline; "
    "a 6-room residential apartment plan; and a complex, real-world commercial shopping mall plan featuring 33 retail and dining units. "
    "All benchmarks ran on standard commodity CPU hardware without GPU acceleration. The entire pipeline—from raw image loading "
    "to complete graph synthesis—executes in approximately 2.0 seconds.'\n"
    "Time: 1 minute.\n"
    "Transition: 'Here are the quantitative results across these benchmarks.'"
)

# =========================================================================
# SLIDE 10: Results & Automated Verification
# =========================================================================
add_slide_with_notes(
    prs,
    "Empirical Results & Test Suite Verification",
    [
        "• 117 / 117 Passing Automated Tests: Verified via pytest across 8 test suites in ~55s on CPU.",
        "• Commercial Mall Generalization: Increased valid room yield from 5 fragmented artifacts (before fixes) to 33 genuine retail units with 38 doors and 118 walls.",
        "• Topological Connectivity: Sample (100% connected), Apartment (100% connected), Mall (32/33 units connected).",
        "• Route Verification: Successfully executes complex multi-hop journeys (e.g. 13-hop route Room_10 -> Room_20 across the mall).",
        "• Scientific Rigor: We report verifiable structural metrics (counts, connectivity, test pass rates) rather than unverified synthetic precision/recall percentages."
    ],
    "SPEAKER NOTES (Slide 10 - Results & Verification):\n"
    "Say: 'Our automated test suite contains 117 unit and integration tests covering every single stage of the system, and all 117 tests pass. "
    "On the real-world mall plan, our typographic suppression and adaptive gap closing resolved a massive failure mode: "
    "before our fixes, text artifacts caused the mall to fragment into just 5 distorted rooms. After our fixes, MapMind accurately extracts "
    "33 genuine retail stores, 38 functional doors, and 118 structural walls. Furthermore, we maintain scientific integrity: "
    "because raster floor plans lack pixel-level CAD ground-truth masks, we report verified topological metrics rather than fabricated accuracy numbers.'\n"
    "Time: 1.5 minutes.\n"
    "Transition: 'Every robust engineering paper must transparently disclose its limitations.'"
)

# =========================================================================
# SLIDE 11: Limitations & Threats to Validity
# =========================================================================
add_slide_with_notes(
    prs,
    "Limitations & Threats to Validity",
    [
        "• Absence of Bundled OCR: Rooms receive structural IDs (Room_1...Room_N) rather than printed brand names (Starbucks, Pharmacy).",
        "• Manhattan-World Assumption: Hough line detection and segment merging assume predominantly orthogonal walls; curved walls may over-segment.",
        "• Isolated Architectural Nodes: Rare flush sliding gates (such as Room_26 in the mall) lack conventional door clearance and remain unlinked.",
        "• Single-Floor 2D Topology: Does not currently model vertical inter-floor transitions (elevators, stairs, escalators).",
        "• Pixel Metric Scale: Traversal distances are measured in pixel units; physical meter calibration requires a known reference scale."
    ],
    "SPEAKER NOTES (Slide 11 - Limitations):\n"
    "Say: 'In accordance with rigorous academic standards, we clearly document our limitations. First, without a bundled OCR engine, "
    "rooms are identified by structural IDs rather than printed store names. Second, our line-merging algorithms assume orthogonal walls "
    "and may struggle with freeform circular architecture. Third, flush sliding gates like Room 26 in the mall can cause isolated nodes. "
    "And fourth, MapMind currently operates in 2D single-floor environments and measures distances in pixels rather than calibrated meters.'\n"
    "Time: 1 minute.\n"
    "Transition: 'To conclude, let us summarize our contribution and future outlook.'"
)

# =========================================================================
# SLIDE 12: Conclusion & Future Outlook
# =========================================================================
add_slide_with_notes(
    prs,
    "Conclusion, Future Work & 60-Second Pitch",
    [
        "• Key Takeaway: MapMind demonstrates that classical computer vision, topological graphs, and local LLMs can deliver robust, private indoor navigation on CPU.",
        "• Verifiable Quality: 117 passing regression tests guarantee architectural integrity and prevent regressions.",
        "• Future Direction 1: Integrate lightweight neural OCR (Tesseract / PaddleOCR) for automatic store directory discovery.",
        "• Future Direction 2: Multi-floor 3D spatial graphs linking floors via stair and elevator nodes.",
        "• Future Direction 3: User-in-the-loop interactive Streamlit canvas allowing manual door and room editing.",
        "• 60-Second Pitch: MapMind turns any floor-plan image into a navigable, door-aware graph on CPU with grounded local LLM guidance—completely private, transparent, and reproducible."
    ],
    "SPEAKER NOTES (Slide 12 - Conclusion & Pitch):\n"
    "Say: 'In conclusion, MapMind proves that classical computer vision and topological graph algorithms remain exceptionally powerful. "
    "By combining them with local, grounded LLMs, we provide an indoor navigation platform that is transparent, fast, private, and fully test-certified. "
    "Our future work will introduce lightweight OCR for semantic store discovery and extend the graph to multi-story buildings. "
    "Thank you very much for your time and attention. I am now delighted to answer your questions.'\n"
    "Time: 1 minute.\n"
    "Transition: 'Floor is now open for viva examination questions.'"
)

output_pptx = r"C:\Users\shive\mapmind\research_deliverables\MapMind_Project_Presentation.pptx"
prs.save(output_pptx)
print(f"[SUCCESS] 12-slide Widescreen Presentation with Embedded Speaker Notes saved to {output_pptx}")

