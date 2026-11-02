from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN

prs = Presentation()

# Add first slide using the Title Slide layout (index 0)
slide1 = prs.slides.add_slide(prs.slide_layouts[0])
slide1.shapes.title.text = "MapMind: Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local LLMs"
# optional: add a subtitle text box if needed, but we'll leave it blank

# Helper function to add a slide with title and content using layout index 1
def add_content_slide(prs, title_text, content_bullets):
    slide = prs.slides.add_slide(prs.slide_layouts[1])  # Title + Content
    slide.shapes.title.text = title_text
    tf = slide.placeholders[1].text_frame
    tf.clear()
    for bullet in content_bullets:
        p = tf.add_paragraph()
        p.text = bullet
        p.font.size = Pt(18)
        p.space_after = Pt(6)
    return slide

# --- Slide 2: Problem Statement ---
add_content_slide(prs, "Problem Statement and Motivation", [
    "Indoor navigation lacks GPS signal",
    "Static floor‑plan images are the only map source",
    "Manual annotation is expensive and time‑consuming",
    "Need for privacy‑preserving, offline LLM interaction"
])

# --- Slide 3: Research Gap and Objectives ---
add_content_slide(prs, "Research Gap and Objectives", [
    "Limited work on combining CV pipeline with local LLM for navigation",
    "Existing floor‑plan parsers lack door‑center‑aware routing",
    "Goal: end‑to‑end system from image to natural‑language route",
    "Objectives: preprocessing, door detection, graph construction, NLQ, route visualization"
])

# --- Slide 4: Related Work ---
add_content_slide(prs, "Related Work", [
    "CubiCasa5K, R2V, Deep Floor Plan Recognition (ICCV 2019)",
    "Indoor positioning surveys (IEEE ComSurv 2020)",
    "A* and Dijkstra for graph pathfinding (1968, 1959)",
    "Tesseract OCR (ICDAR 2007)",
    "Ollama and local LLM deployment (2024)"
])

# --- Slide 5: System Architecture ---
add_content_slide(prs, "System Architecture", [
    "Streamlit UI → Floor‑plan image",
    "CV pipeline (OpenCV): binarisation → wall closing → region segmentation → door probing",
    "Navigation graph (NetworkX): nodes = rooms/corridors, edges = doors with centre‑to‑door distances",
    "Query parser (intent‑only): navigate, where_is, how_many",
    "Ollama LLM (optional): deterministic fallback, clarification prompts",
    "Route overlay (draw_route_overlay): centre → door → centre arrows"
])

# --- Slide 6: CV & floor‑plan understanding pipeline ---
add_content_slide(prs, "Computer Vision & Floor‑Plan Understanding", [
    "Binarisation (adaptive threshold, Otsu)",
    "Morphological closing & gap selection (segmentation_gap_candidates)",
    "Canny edge detection & Hough line detection",
    "Wall merging (merge_angle_deg, merge_distance_ratio)",
    "Region segmentation (_segment_regions) → rooms & corridors",
    "Door detection (_detect_and_associate_doors): symbol + region‑gap candidates",
    "Probe‑along‑orientation to find connected regions",
    "Result: rooms, corridors, doors with centres and connected_regions"
])

# --- Slide 7: Location inventory & navigation graph ---
add_content_slide(prs, "Location Inventory & Navigation Graph", [
    "Rooms: Room_1 … Room_N (centre, bounding_box, area)",
    "Corridors: Corridor_1 (centre, bounding_box, area)",
    "Doors: Door_1 … Door_M (centre, orientation, connected_regions, detection_method)",
    "Graph nodes = room/corridor names",
    "Graph edges = door connections, weight = centre→door + door→centre distance",
    "Isolated nodes recorded (e.g., Room_26 in apartment)",
    "A* shortest‑path with heuristic ‖center_u – center_v‖"
])

# --- Slide 8: NLQ processing & local LLM ---
add_content_slide(prs, "Natural‑Language Query & Local LLM", [
    "Query parser (llm/query_parser.py) extracts intent + slots",
    "Known intents: navigate(s,d), where_is(x), how_many()",
    "Free‑text queries → clarification_needed prompt",
    "Ollama client (llm/ollama_client.py) selects model from .env.example",
    "use_llm=False → parser‑only path; use_llm=True → invoke Ollama",
    "Fallback: deterministic answer or 'I cannot answer that'."
])

# --- Slide 9: Experimental setup ---
add_content_slide(prs, "Experimental Setup", [
    "Python 3.12, OpenCV 4.x, NetworkX 3.3, Streamlit 1.38",
    "Floor‑plans: sample (5 rooms/1 corridor), Apartment (6 rooms/1 corridor), Mall (33 rooms/1 corridor)",
    "Test suite: 117 unit/integration tests, all pass",
    "Parsing time ≈ 2 s for 650 × 904 image",
    "Hardware: CPU only, no GPU required",
    "Ollama not running during audit; client code present and import‑able"
])

# --- Slide 10: Results and limitations ---
add_content_slide(prs, "Results and Limitations", [
    "117/117 tests pass",
    "Wall count: 60 (apt), 118 (mall)",
    "Room count: 6 (apt), 5 (sample), 33 (mall)",
    "Door count: 6 (apt), 38 (mall)",
    "Graph: apartment & sample connected; mall has isolated Room_26",
    "Route success: apt Room_2→Room_3 via Corridor_1; sample Room_1→Room_5; mall Room_10→Room_20 (13 hops)",
    "NLQ: canonical intents succeed; free‑text → clarification",
    "Limitations: no OCR, isolated rooms, limited NLU, image‑resolution dependent"
])

# --- Slide 11: Conclusion and future work ---
add_content_slide(prs, "Conclusion and Future Work", [
    "MapMind demonstrates that a pure CV pipeline + graph + local LLM can turn a floor‑plan into a navigable representation",
    "117 tests certify structural correctness",
    "Future: integrate OCR for semantic labels, user‑correction UI, expand NLQ intent set, evaluate on public datasets (CubiCasa5K, R2V)",
    "Multi‑floor / 3‑D building models, confidence‑aware graph, user‑correctable map generation"
])

# --- Slide 11.5: Questions (optional) - we'll add as slide 11, then slide 12 for pitch; but we already have 11 slides so far. Let's add a questions slide as slide 11, and pitch as slide 12.

# --- Slide 11: Questions ---
add_content_slide(prs, "Questions", [
    "Q1: How do you handle complex multi‑floor layouts?",
    "Q2: What if the OCR backend is added?",
    "Q3: Can the system handle non‑orthogonal floor plans?"
])

# --- Slide 12: 60‑second pitch ---
add_content_slide(prs, "60‑Second Pitch", [
    "MapMind turns a single floor‑plan image into a navigable graph using classical computer‑vision, "
    "enables routes annotated with the exact doors used, and answers a small set of natural‑language queries "
    "via a locally hosted LLM, all without uploading data to the cloud. "
    "The system is fully test‑covered (117 tests) and runs on CPU, making it suitable for privacy‑sensitive "
    " indoor navigation scenarios."
])

# Save PPTX
pptx_path = r"C:\Users\shive\mapmind\research_deliverables\MapMind_Project_Presentation.pptx"
prs.save(pptx_path)
print("PPTX saved to", pptx_path)
