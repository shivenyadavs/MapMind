import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = docx.Document()

for s in doc.sections:
    s.top_margin = Inches(1)
    s.bottom_margin = Inches(1)
    s.left_margin = Inches(1)
    s.right_margin = Inches(1)

DARK_BLUE = RGBColor(16, 44, 87)
ACCENT_BLUE = RGBColor(53, 114, 239)
TEXT_DARK = RGBColor(30, 30, 30)

def add_header(title, subtitle=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(title)
    run.font.name = "Arial"
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = DARK_BLUE
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if subtitle:
        p2 = doc.add_paragraph()
        p2.paragraph_format.space_after = Pt(12)
        r2 = p2.add_run(subtitle)
        r2.font.name = "Calibri"
        r2.font.size = Pt(12)
        r2.font.italic = True
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER

def add_slide_section(slide_num, title, time_str, key_point, speech, transition, examiner_q=None):
    p_h = doc.add_paragraph()
    p_h.paragraph_format.space_before = Pt(14)
    p_h.paragraph_format.space_after = Pt(2)
    r_h = p_h.add_run(f"Slide {slide_num}: {title}")
    r_h.font.name = "Arial"
    r_h.font.size = Pt(14)
    r_h.font.bold = True
    r_h.font.color.rgb = DARK_BLUE

    # Meta
    p_m = doc.add_paragraph()
    p_m.paragraph_format.space_after = Pt(4)
    r_time = p_m.add_run(f"Allocated Time: {time_str} | ")
    r_time.font.bold = True
    r_time.font.size = Pt(10)
    r_kp_lbl = p_m.add_run("Core Objective: ")
    r_kp_lbl.font.bold = True
    r_kp_lbl.font.size = Pt(10)
    r_kp = p_m.add_run(key_point)
    r_kp.font.size = Pt(10)

    # Word-for-Word Spoken Delivery
    p_s = doc.add_paragraph()
    p_s.paragraph_format.space_before = Pt(2)
    p_s.paragraph_format.space_after = Pt(4)
    p_s.paragraph_format.left_indent = Inches(0.2)
    r_s_lbl = p_s.add_run("What to Say (Word-for-Word):\n")
    r_s_lbl.font.bold = True
    r_s_lbl.font.color.rgb = ACCENT_BLUE
    r_s_lbl.font.size = Pt(10.5)
    r_s = p_s.add_run(f'"{speech}"')
    r_s.font.size = Pt(10.5)
    r_s.font.italic = True

    # Transition
    p_t = doc.add_paragraph()
    p_t.paragraph_format.space_after = Pt(4)
    r_t_lbl = p_t.add_run("Verbal Transition: ")
    r_t_lbl.font.bold = True
    r_t_lbl.font.size = Pt(10)
    r_t = p_t.add_run(f'"{transition}"')
    r_t.font.size = Pt(10)

    if examiner_q:
        p_q = doc.add_paragraph()
        p_q.paragraph_format.space_after = Pt(6)
        r_q_lbl = p_q.add_run("Anticipated Examiner Question & Quick Defense: ")
        r_q_lbl.font.bold = True
        r_q_lbl.font.size = Pt(9.5)
        r_q_lbl.font.color.rgb = RGBColor(120, 40, 40)
        r_q = p_q.add_run(examiner_q)
        r_q.font.size = Pt(9.5)

add_header("MapMind: Master Presentation Speaking Script", 
           "Complete Slide-by-Slide Spoken Narration, Timing Guides, Transitions, and Defense Tactics")

# Slide 1
add_slide_section(
    1, "Title Slide & Project Introduction",
    "45 seconds",
    "Establish the research identity, authors, and edge-deployable premise.",
    "Good morning, respected examiners and committee members. Today I am proud to present MapMind: "
    "Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local Large Language Models. "
    "MapMind is a complete, fully offline, edge-deployable indoor navigation platform that transforms unannotated architectural "
    "floor plans into structured, door-aware topological navigation graphs, enabling conversational wayfinding without cloud APIs, "
    "without GPU hardware, and without manual map tagging.",
    "Let us begin by examining the core problem that makes indoor navigation so challenging.",
    "Why not use cloud APIs? Answer: In hospitals, government institutions, and commercial real estate, building floor plans and visitor queries are confidential. MapMind guarantees 100% on-device data sovereignty."
)

# Slide 2
add_slide_section(
    2, "Problem Statement: The Indoor Navigation Void",
    "1 minute",
    "Highlight satellite GPS attenuation, physical beacon fragility, and raster floor-plan realities.",
    "While outdoor navigation is solved by GPS, indoor navigation remains an infrastructure void. Once a user steps inside "
    "a hospital or large shopping mall, GPS signals drop to zero. The current industry standard requires either installing hundreds "
    "of physical Bluetooth beacons—which are expensive, battery-dependent, and fragile—or forcing users to decipher static, unannotated raster images. "
    "Furthermore, commercial facilities cannot upload proprietary building layouts to external cloud AI services due to privacy and security compliance.",
    "This brings us directly to the research gap and our core project objectives.",
    "Why are BLE beacons inadequate? Answer: Beacons cost $20-$50 each, require battery replacements every 12-24 months, and require continuous site recalibration whenever furniture or walls move."
)

# Slide 3
add_slide_section(
    3, "Research Gap & Objectives",
    "1 minute 15 seconds",
    "Explain the dichotomy between neural vectorizers and naive centroid paths; state our 3 core goals.",
    "Existing research has two major shortcomings: deep learning vectorizers require thousands of annotated floor plans and server GPUs, "
    "while basic topological parsers connect room centers directly, producing routes that clip straight through solid walls. "
    "MapMind bridges this gap with three concrete objectives: first, an algorithmic CPU-based classical CV parser; second, a door-center-aware graph engine; "
    "and third, an offline local LLM interface with strict grounding guardrails that guarantee zero spatial hallucinations.",
    "Let us briefly place this in the context of existing literature.",
    "How does your door-center approach differ from prior art? Answer: Prior parsers either draw direct straight lines between room centers (wall-clipping) or use fine pixel grids (computationally slow). We route piecewise: room centroid to door threshold to room centroid."
)

# Slide 4
add_slide_section(
    4, "Related Work & Prior Benchmarks",
    "1 minute",
    "Position MapMind against CubiCasa5K, R2V, A* shortest path, and local LLM runtimes.",
    "Our work builds on established foundations across four domains: the indoor positioning taxonomies of Liu and Zafari; "
    "the floor plan vectorization benchmarks of CubiCasa5K and Raster-to-Vector; the classical topological mapping work of Macé and Afzal; "
    "and the foundational A* search algorithm of Hart et al. Unlike deep learning approaches that require massive training data, "
    "MapMind achieves deterministic vectorization using classical CV and connects it directly to local LLMs.",
    "Here is how the four layers of MapMind fit together in our system architecture.",
    "Why not fine-tune a YOLO or Mask R-CNN model? Answer: Deep models require thousands of labeled CAD masks, fail on novel drafting styles, and require GPUs. Our classical CV pipeline runs in 2 seconds on CPU with zero training data."
)

# Slide 5
add_slide_section(
    5, "MapMind End-to-End System Architecture",
    "1 minute 15 seconds",
    "Walk through the 4 architectural layers: UI, CV, Graph, and Grounded Local LLM.",
    "The MapMind architecture is structured into four tightly coordinated layers: the Streamlit user interface; "
    "the classical computer vision engine implemented in OpenCV; the topological graph and pathfinding engine in NetworkX; "
    "and the grounded local LLM module in Ollama. Crucially, all four layers execute completely on the local host CPU. "
    "No floor plans or user queries are ever transmitted across the network, guaranteeing total privacy.",
    "Let us examine the algorithmic steps of our computer vision pipeline.",
    "What is the system bottleneck? Answer: The CV pipeline takes ~2s, while graph pathfinding takes under 5ms. If local LLM explanation is toggled on, quantized CPU inference takes ~2-4s depending on the local model."
)

# Slide 6
add_slide_section(
    6, "Computer Vision & Structural Feature Extraction",
    "1 minute 30 seconds",
    "Explain color thresholding, text suppression, adaptive gap closing, Hough lines, and door probing.",
    "Our computer vision pipeline solves the core challenges of floor plan parsing without neural networks. "
    "First, we separate dark walls from colored architectural markings. Second, our typographic text suppression algorithm "
    "removes printed labels like STORE or ROOM 101, which otherwise fracture rooms into dozens of tiny pieces. "
    "Third, adaptive gap closing tests six morphological kernel sizes to seal wall openings without bridging doorways. "
    "Fourth, Hough lines are merged into clean structural walls. Finally, connected components separate rooms from corridors, "
    "and our orthogonal ray probe links doors directly to their parent rooms.",
    "Once architectural features are extracted, how do we construct the navigation graph?",
    "Why did the mall floor plan initially fail? Answer: High-contrast printed text labels (like 'STORE') were treated as walls by adaptive thresholding, fragmenting the mall into tiny micro-regions. Our typographic bounding-box filter completely eliminated this bug."
)

# Slide 7
add_slide_section(
    7, "Location Inventory & Topological Graph Synthesis",
    "1 minute 15 seconds",
    "Detail vertex creation, door-center edge weighting, A* admissibility, and overlay rendering.",
    "From the extracted inventory, NetworkX synthesizes an undirected topological graph. Nodes are room centroids, "
    "and edges represent verified doors. Unlike naive graphs that use hop counts or direct centroid lines, MapMind calculates "
    "the exact walking distance: from room centroid, through the physical door threshold, to the next room centroid. "
    "Our A* pathfinder uses an admissible Euclidean heuristic that guarantees shortest paths. When we draw the route overlay, "
    "it visually threads through the door opening rather than cutting across solid concrete walls.",
    "Now, how does a user interact with this graph using natural language?",
    "Is your A* heuristic admissible? Answer: Yes, the Euclidean distance between room centroids h(u, t) = ||c(u) - c(t)|| satisfies the triangle inequality and never overestimates the true traversal cost, guaranteeing mathematical optimality."
)

# Slide 8
add_slide_section(
    8, "Natural-Language Query & Grounded Local LLMs",
    "1 minute 15 seconds",
    "Explain regex slot-filling, local Ollama execution, and the Grounding Rejection mechanism.",
    "For conversational interaction, user queries are first evaluated by our fast query parser to identify the intent and extract room entities. "
    "If conversational explanations are requested, we invoke a local LLM such as Microsoft Phi or Llama-3 through Ollama. "
    "However, to solve the well-known LLM hallucination problem, we built a strict Grounding Rejection layer: if the LLM mentions any room "
    "not in the computed route or invents unverified turn instructions, the output is discarded and replaced with our deterministic rule-based explanation. "
    "The user always receives 100% verified directions.",
    "Let us look at our experimental setup and evaluation environments.",
    "What happens if Ollama is not installed or offline? Answer: The navigation service implements graceful fallback: it automatically catches connection errors and answers via our rule-based response generator without interrupting the user."
)

# Slide 9
add_slide_section(
    9, "Experimental Setup & Benchmark Environments",
    "1 minute",
    "Summarize Python/OpenCV/NetworkX stack and introduce the Sample, Apartment, and Mall benchmarks.",
    "We rigorously tested MapMind across three distinct architectural layouts: a 5-room academic baseline; "
    "a 6-room residential apartment plan; and a complex, real-world commercial shopping mall plan featuring 33 retail and dining units. "
    "All benchmarks ran on standard commodity CPU hardware without GPU acceleration. The entire pipeline—from raw image loading "
    "to complete graph synthesis—executes in approximately 2.0 seconds.",
    "Here are the quantitative results across these benchmarks.",
    "Why test on a commercial mall? Answer: Academic samples are often idealized. A real-world mall tests resilience against complex store grids, dense door clusters, and extensive printed text."
)

# Slide 10
add_slide_section(
    10, "Empirical Results & Test Suite Verification",
    "1 minute 30 seconds",
    "Present Table I, mall unit recovery (from 5 to 33 rooms), and the 117-test passing suite.",
    "Our automated test suite contains 117 unit and integration tests covering every single stage of the system, and all 117 tests pass. "
    "On the real-world mall plan, our typographic suppression and adaptive gap closing resolved a massive failure mode: "
    "before our fixes, text artifacts caused the mall to fragment into just 5 distorted rooms. After our fixes, MapMind accurately extracts "
    "33 genuine retail stores, 38 functional doors, and 118 structural walls. Furthermore, we maintain scientific integrity: "
    "because raster floor plans lack pixel-level CAD ground-truth masks, we report verified topological metrics rather than fabricated accuracy numbers.",
    "Every robust engineering paper must transparently disclose its limitations.",
    "Why is Room 26 isolated in the mall? Answer: Room 26 is a small kiosk unit with a flush sliding security gate rather than an open door swing. The morphological closing bridged the narrow opening, preventing ray probes from finding an adjoining region. The UI cleanly warns the user that Room 26 is isolated."
)

# Slide 11
add_slide_section(
    11, "Limitations & Threats to Validity",
    "1 minute",
    "Acknowledge OCR absence, Manhattan-world assumptions, single-floor scope, and pixel distance units.",
    "In accordance with rigorous academic standards, we clearly document our limitations. First, without a bundled OCR engine, "
    "rooms are identified by structural IDs rather than printed store names. Second, our line-merging algorithms assume orthogonal walls "
    "and may struggle with freeform circular architecture. Third, flush sliding gates like Room 26 in the mall can cause isolated nodes. "
    "And fourth, MapMind currently operates in 2D single-floor environments and measures distances in pixels rather than calibrated meters.",
    "To conclude, let us summarize our contribution and future outlook.",
    "Can you integrate OCR later? Answer: Yes. The architecture features an explicit OCR hook in cv/floorplan_parser.py. If Tesseract or PaddleOCR is installed, detected words are mapped to room bounding boxes via spatial containment."
)

# Slide 12
add_slide_section(
    12, "Conclusion, Future Work & 60-Second Pitch",
    "1 minute 15 seconds",
    "Deliver the final synthesis, future roadmap (OCR, 3D multi-floor, interactive editing), and pitch.",
    "In conclusion, MapMind proves that classical computer vision and topological graph algorithms remain exceptionally powerful. "
    "By combining them with local, grounded LLMs, we provide an indoor navigation platform that is transparent, fast, private, and fully test-certified. "
    "Our future work will introduce lightweight OCR for semantic store discovery and extend the graph to multi-story buildings. "
    "Thank you very much for your time and attention. I am now delighted to answer your questions.",
    "Thank you. The floor is now open for examination questions.",
    "What is your immediate next step? Answer: Implementing the interactive Streamlit user-correction canvas so that facility managers can click to add or adjust doors on ambiguous architectural drawings."
)

output_script = r"C:\Users\shive\mapmind\research_deliverables\MapMind_Speaking_Script.docx"
doc.save(output_script)
print(f"[SUCCESS] Complete Speaking Script saved to {output_script}")

