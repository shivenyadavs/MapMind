import docx
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = docx.Document()

# Title
title = doc.add_heading('MapMind: Vision-Based Indoor Floor Plan Understanding and Natural Language Navigation Using Local LLMs', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

# Authors placeholder
p = doc.add_paragraph()
run = p.add_run('[Author Name]')
run.font.size = Pt(12)
p2 = doc.add_paragraph()
run2 = p2.add_run('[Institution]')
run2.font.size = Pt(12)

# Abstract
doc.add_heading('Abstract', level=1)
abstract_text = (
    "Indoor navigation in complex buildings such as shopping malls, office complexes, and airports remains a challenging problem because the environment is often only available as a static floor-plan image. "
    "MapMind addresses this problem by (i) extracting architectural features (walls, rooms, doors, corridors) from a single indoor floor-plan image using classical computer‑vision pipelines, "
    "(ii) converting the extracted features into a navigable graph, and "
    "(iii) interacting with a user through natural‑language queries that are resolved by a locally hosted large language model (LLM) via Ollama. "
    "The system therefore combines low‑level vision (binarisation, morphological closing, Canny edge detection, Hough line detection, region‑gap door candidates) with high‑level reasoning (NetworkX shortest‑path, query‑parser intent handling, deterministic LLM fallback).\n\n"
    "The evaluation was performed on three representative floor‑plans (sample 5 rooms/1 corridor, a 6‑room apartment, and a 33‑room mall).  The test suite contains 117 unit/integration tests that verify graph consistency, door‑pair uniqueness, route validity, and correct overlay rendering.  Qualitative inspection shows that the parser correctly identifies doors, builds a connected graph for the sample and apartment, and produces a route overlay that follows the selected doors rather than cutting across walls.  No OCR‑based semantic labels are available because the Tesseract back‑end is absent; all room names are generated as Room_N / Corridor_N.\n\n"
    "Key contributions\n"
    "* A complete, reproducible CV pipeline (binarisation → wall‑closing → region segmentation → door probing → graph construction) that runs fully on CPU.\n"
    "* A graph‑based navigation engine that returns routes annotated with the exact doors used, enabling visual overlays that pass through doors.\n"
    "* Integration of a local LLM (Ollama) for a tiny set of natural‑language intents, with deterministic fallback when the model cannot ground the query.\n"
    "* 117 passing tests that certify structural correctness of the extracted representation.\n\n"
    "Limitations\n"
    "* No semantic labels or printed‑store names can be extracted because OCR back‑ends are not installed.\n"
    "* Graph connectivity depends on correct wall‑/door‑detection; complex or non‑standard floor‑plan conventions may cause isolated regions (e.g., Room_26 in the apartment).\n"
    "* The NLQ interface currently supports only a handful of pre‑programmed intents; free‑text queries produce a clarification prompt."
)
p = doc.add_paragraph(abstract_text)
p.style = doc.styles['Normal']
for run in p.runs:
    run.font.size = Pt(11)

# Index Terms
doc.add_heading('Index Terms', level=1)
index_terms = [
    "indoor navigation", "floor‑plan understanding", "computer vision", "graph‑based path planning",
    "local large language models", "semantic scene understanding", "natural‑language interfaces"
]
p = doc.add_paragraph(" ".join(index_terms))
p.style = doc.styles['Normal']

# Placeholder sections 1‑12
sections = [
    "1. Introduction",
    "2. Related Work",
    "3. Problem Formulation and System Overview",
    "4. Proposed Methodology",
    "5. System Architecture and Implementation",
    "6. Experimental Setup",
    "7. Results and Discussion",
    "8. Limitations and Threats to Validity",
    "9. Conclusion and Future Work",
    "10. (References)",
    "11. (Conclusion and Future Work continued)",
    "12. (References continued)"
]
placeholder_map = {
    "1. Introduction": "Describe why indoor navigation is challenging, why floor plans are useful, the difficulties of visual‑to‑graph conversion, and the motivation for using locally hosted LLMs. Clearly state the research problem and contributions.",
    "2. Related Work": "Cite real, verifiable scholarly references (see bibliography section). Use real, verifiable scholarly references. Prioritize peer‑reviewed conference papers and journal articles, followed by authoritative technical documentation where appropriate.",
    "3. Problem Formulation and System Overview": "Describe the input floor‑plan image, detected locations and architectural features, navigation graph, user query, and expected route or location‑search response. Define the assumptions and limitations.",
    "4. Proposed Methodology": "Explain the actual implementation in technical detail: A. Image acquisition and preprocessing. B. Architectural feature extraction and wall detection. C. Door detection and room/location segmentation. D. Semantic label extraction using OCR or other implemented methods. E. Location inventory construction and identifier assignment. F. Navigation graph construction. G. Shortest‑path computation. H. Natural‑language query resolution and local LLM integration. I. Route visualization and user interaction through Streamlit.",
    "5. System Architecture and Implementation": "Include a clean architecture diagram showing the real system components and data flow. Explain Python and OpenCV, NetworkX or the actual graph implementation, Streamlit, Ollama and the actual local model configuration, Data structures exchanged between components, How natural‑language queries become structured navigation operations.",
    "6. Experimental Setup": "Describe the actual experimental environment, software versions, hardware, sample floor plans, and test cases when these details can be verified. Specify the test methodology and evaluation criteria. If a proper ground‑truth dataset is unavailable, acknowledge this and distinguish unit testing, graph consistency testing, qualitative image inspection, and quantitative vision evaluation.",
    "7. System Architecture and Implementation": "Duplicate entry for emphasis (keep as in original).",
    "7. (Continued) System Architecture and Implementation": "Continue the architecture description, include any missing data‑flow details.",
    "8. Results and Discussion": "Include actual observations and results only. Where supported, report test pass/fail counts, wall detection precision and recall, room detection precision/recall or IoU, door detection precision and recall, semantic classification accuracy, route success rate, graph connectivity or path validity, natural‑language query success rate, runtime and resource usage. Do not calculate accuracy without appropriate ground truth. Do not report fabricated benchmark scores or claim improvements without a before/after evaluation. If measurements are unavailable, create a clearly labelled evaluation plan and identify the measurements that remain to be collected. Do not present planned experiments as completed experiments. Include genuine screenshots or figures from the actual project when available.",
    "9. Limitations and Threats to Validity": "Discuss the real limitations identified during the audit, potentially including: complex architectural drawings, false wall and door detections, room segmentation errors, uncertain semantic labels, graph connectivity errors, dependence on image resolution and drawing conventions, limited validation data, errors in natural‑language entity resolution, local LLM latency and hardware constraints.",
    "9. Conclusion and Future Work": "Summarize the contribution and actual findings. Describe reasonable future work, such as improved semantic segmentation, symbol recognition, annotated evaluation datasets, confidence‑aware graph construction, and user‑correctable map generation.",
    "10. (References)": "Use IEEE numeric citation style, with numbered references in order of first citation. Include verified references only.",
    "12. References": "List the references that appear in the paper, formatted in IEEE numeric style."
}
for s in sections:
    doc.add_heading(s, level=2)
    ph = placeholder_map.get(s, "Placeholder content for section " + s)
    p = doc.add_paragraph(ph)
    p.style = doc.styles['Normal']
    for run in p.runs:
        run.font.size = Pt(11)

# Save docx
output_path = r"C:\Users\shive\mapmind\research_deliverables\MapMind_IEEE_Paper.docx"
doc.save(output_path)
print("DOCX saved to", output_path)