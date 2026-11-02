"""Build the completed Invention Disclosure Form (IDF) for MapMind.

Generates two files in research_deliverables/:
  - MapMind_IPR_Invention_Disclosure_Form.docx  (python-docx)
  - MapMind_IPR_Invention_Disclosure_Form.pdf   (ReportLab)
Content is derived from the supplied project materials:
README.md, MapMind_IEEE_Paper, cv/pipeline_config.py, and the graph/llm modules.
"""

import os

from PIL import Image as PILImage

import build_idf_figures

build_idf_figures.build_all()

BASE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(BASE, "research_deliverables", "ieee_latex", "figures")
OUT_DIR = os.path.join(BASE, "research_deliverables")
DOCX_PATH = os.path.join(OUT_DIR, "MapMind_IPR_Invention_Disclosure_Form.docx")
PDF_PATH = os.path.join(OUT_DIR, "MapMind_IPR_Invention_Disclosure_Form.pdf")

CHECK_ON = "\u2611"   # ballot box with check
CHECK_OFF = "\u2610"  # empty ballot box

TBC = "To be confirmed at submission"
NPS = "Not provided in the supplied materials - confirmation required"

# --------------------------------------------------------------------------
# Content blocks (single source of truth for both DOCX and PDF)
# Block kinds: title, subtitle, h1, h2, p, pi, bullets, num, table, check,
#              figpair, spacer
# --------------------------------------------------------------------------

BLOCKS = []
B = BLOCKS.append

B(("title", "Invention Disclosure Form (IDF)"))
B(("subtitle", "MapMind: Vision-Based Indoor Floor Plan Understanding and Natural-Language "
               "Navigation Using Local Large Language Models"))
B(("p", "Date of Submission: ______________________________  "
        "(to be completed at the time of actual submission; no date is fixed in the supplied materials)."))
B(("p", "A patent application must meet the following criteria in order to apply for patent: "
        "the invention must be new (novel), must involve an inventive step (non-obviousness), must be capable of "
        "industrial application, and must be fully disclosed in the application. The present disclosure is prepared "
        "on this basis."))

B(("h1", "Stages of Completion of Project (Tick the appropriate)"))
B(("check", [
    ("Ideation", False),
    ("Ongoing work", False),
    ("Prototype", False),
    ("Working model", True),
    ("Results Validated", False),
]))
B(("pi", "Selection note: the complete end-to-end system (CV pipeline, graph construction, A* routing, grounded local "
         "LLM interface and interactive web application) is fully implemented and runs offline on commodity CPU "
         "hardware, qualifying MapMind as a working model. \u2018Results Validated\u2019 is not ticked because all results "
         "to date come from internal testing (117 automated regression tests and three bundled demo plans); no "
         "independent or ground-truth benchmark evaluation has yet been performed."))

B(("h1", "Following details must be provided by the inventor(s) who wishes to apply for patent:"))

B(("h2", "1. Title of Invention"))
B(("p", "\u201cMapMind: A Vision-Based Indoor Floor Plan Understanding and Natural-Language Navigation System Using "
        "Local Large Language Models\u201d \u2014 an end-to-end, fully offline software system that automatically "
        "converts an unannotated 2D raster architectural floor-plan image into a navigable topological graph and "
        "answers natural-language navigation queries with hallucination-guarded, locally hosted LLMs."))

B(("h2", "2. List All Inventors"))
B(("table", {
    "header": ["Field", "Inventor 1 - Details"],
    "rows": [
        ["Name", "Dr. Seema Bangareswara Hegde"],
        ["Designation", "Professor"],
        ["Department", "Department of Computer Science and Engineering (CSE)"],
        ["Address", "Global Academy of Technology, Ideal Home Town, R R Nagar, Bengaluru-98"],
        ["Email and phone number", NPS],
        ["Nationality", "Indian"],
    ],
}))
B(("table", {
    "header": ["Field", "Inventor 2 - Details"],
    "rows": [
        ["Name", TBC + " \u2014 student inventor(s) of the MapMind project; names are not stated in the supplied "
                       "project materials (the attached technical report contains placeholder author fields)"],
        ["Designation", TBC],
        ["Department", TBC],
        ["Address", TBC],
        ["Email and phone number", TBC],
        ["Nationality", TBC],
    ],
}))
B(("table", {
    "header": ["Field", "Inventor 3 - Details"],
    "rows": [
        ["Name", TBC],
        ["Designation", TBC],
        ["Department", TBC],
        ["Address", TBC],
        ["Email and phone number", TBC],
        ["Nationality", TBC],
    ],
}))
B(("pi", "Note (please include additional names and details of inventors as needed): inventorship under patent law "
         "reflects actual contribution to the conception of the invention; every student who conceived any claimed "
         "feature must be listed, and those who only implemented assignments must not. The inventor list above must "
         "therefore be finalised by the applicants before filing."))

B(("h2", "3. Is this a funded project?"))
B(("p", "No. (As recorded on the master form. If any institutional or sponsored-project funding is later involved, "
        "the funding body's IP policy must be checked before filing.)"))

B(("h2", "4. Is this work bound by any contractual agreement?"))
B(("p", "No / Not Applicable. (As recorded on the master form; licenses held by building blocks \u2014 e.g., "
        "OpenCV (Apache-2.0), NetworkX (BSD-3), Streamlit (Apache-2.0), Ollama (MIT) \u2014 are permissive "
        "open-source licenses and do not restrict ownership of the invention, but this should be re-confirmed at "
        "filing.)"))

B(("h2", "5. Is the invention a product or a process?"))
B(("p", "Product \u2014 the invention is claimed as an end-to-end navigation software system (product). The "
        "disclosure also covers the associated method of operation of that system, so both a product claim set and "
        "one method claim are proposed (see item 13)."))

B(("h2", "6. Has this work been disclosed to the public before?"))
B(("p", "No. The work has not been published, commercially launched, exhibited or deposited publicly. Internal "
        "academic reviews, viva sessions and supervisor discussions are not counted here; any public presentation, "
        "journal/conference submission or public demo should occur only after the patent application is filed, or "
        "with guidance from the institution's IP cell."))

B(("h2", "7. Proposed Abstract of the Invention"))
B(("p", "Indoor wayfinding in hospitals, campuses and shopping centres is difficult because GPS is unavailable "
        "indoors, while the architectural floor plans such buildings almost always possess are plain raster images "
        "that machines cannot parse: converting them into a navigable representation has so far required manual CAD "
        "tagging, costly beacon deployments (Wi-Fi/BLE/UWB), or deep-learning pipelines needing large annotated "
        "datasets and cloud GPUs. MapMind removes all of these dependencies with a fully offline, edge-deployable "
        "system combining classical computer vision, topological graph pathfinding and privacy-preserving local Large "
        "Language Models. A deterministic multi-stage CV pipeline on a commodity CPU performs resolution "
        "normalisation, adaptive chromatic separation of wall ink from coloured door symbols, text-artifact "
        "suppression, candidate-driven adaptive morphological gap closing, Hough-transform wall merging, and "
        "connected-component segmentation of free space into rooms and corridors. A dual-source door detector "
        "combines colour-based door parsing with region-gap analysis and associates doorways to rooms by orthogonal "
        "ray probing. The extracted elements are synthesised into a weighted NetworkX graph whose edge costs model "
        "exact centroid\u2192door\u2192centroid walking paths, enabling door-centre-aware A* routing. Queries are "
        "answered by locally hosted LLMs (via Ollama) guarded by a deterministic verification layer that rejects "
        "ungrounded spatial claims and substitutes rule-based, route-faithful instructions. A dense 33-unit mall plan "
        "is parsed in about 2.0 s on CPU and the system is backed by 117 passing automated regression tests."))

B(("h2", "8. Key Words"))
B(("p", "Indoor navigation; floor-plan understanding; classical computer vision; morphological gap closing; wall "
        "detection; room segmentation; dual-source door detection; ray probing; topological graph; A* search; "
        "door-centre-aware routing; local Large Language Model; Ollama; grounding verification; edge deployment; "
        "privacy; offline navigation."))

B(("h2", "9. Background of the Invention"))
B(("p", "(i) Indoor positioning is an unsolved infrastructure problem. GPS ends at the building door; inside malls, "
        "hospitals and campuses, satellite signals are attenuated by concrete and steel. Existing remedies \u2014 "
        "dense arrays of BLE beacons, Wi-Fi fingerprinting, UWB anchors \u2014 achieve localised accuracy only while "
        "imposing high hardware cost, maintenance and fragile recalibration."))
B(("p", "(ii) Raster floor plans are universally available but machine-unreadable. Virtually every building has an "
        "architectural floor plan as a static raster image, yet turning it into a navigable network has required "
        "manual CAD vectorisation or deep-learning parsers that need thousands of labelled samples and GPUs."))
B(("p", "(iii) Conversational wayfinding with cloud LLMs raises privacy and hallucination concerns: cloud models "
        "would transmit proprietary layouts and visitor queries to third parties \u2014 unacceptable in corporate, "
        "medical or defence premises \u2014 and their spatial hallucinations (invented rooms, skipped doors, "
        "fabricated turns) are well documented."))
B(("p", "(iv) Naive graph routes render as straight centroid-to-centroid lines that visibly cut through walls because "
        "doorway positions are ignored. No prior approach identified in the applicant's survey combines a "
        "training-free classical CV parser, door-centre-aware weighted routing and a grounded, fully local LLM "
        "interface in one offline product."))

B(("h2", "10. What problems does the invention address and how is it able to overcome the limitations/problems of "
         "the existing technologies?"))
B(("table", {
    "header": ["Limitation of existing technologies", "How MapMind overcomes it"],
    "rows": [
        ["GPS denied indoors; wayfinding depends on staff or fixed signage.",
         "Computes navigation entirely from the building's own raster floor plan \u2014 no satellite or ad-hoc "
         "infrastructure required."],
        ["Beacon systems (Wi-Fi/BLE/UWB) need costly hardware and recurrent calibration.",
         "Zero site-side hardware; deployment reduces to uploading an existing floor-plan image."],
        ["Manual CAD annotation of rooms/doors is slow, error-prone, not scalable.",
         "Classical CV extracts walls, rooms, corridors and doors automatically in seconds, with no annotation."],
        ["Deep-learning parsers need labelled datasets, GPUs, and generalise poorly.",
         "Deterministic geometry-driven CV needs no training data and runs on a commodity CPU."],
        ["Cloud LLM interfaces leak layouts and queries to third parties.",
         "All inference runs on a locally hosted Ollama runtime; no data leaves the machine."],
        ["LLM spatial hallucinations mislead users.",
         "A grounding verifier rejects any LLM text referencing objects outside the computed route or asserting "
         "unsupported turns, and substitutes a rule-based explanation."],
        ["Naive routes cut through walls.",
         "Routes are costed and rendered as centroid \u2192 door-centre \u2192 centroid polylines."],
    ],
}))

B(("h2", "11. Detailed Explanation of the Invention, along with working examples"))
B(("h3", "11.1 System overview"))
B(("p", "MapMind is organised as five cooperating stages, executed in sequence:"))
B(("num", [
    "CV pipeline (OpenCV): parse_floorplan() converts the raster drawing into a structured FloorPlan object "
    "(Pydantic model) holding walls, rooms, corridors, doors and diagnostics.",
    "Graph construction: NavigationGraphBuilder builds an undirected NetworkX graph whose nodes are rooms/corridor "
    "segments and whose edges are doorways.",
    "Navigation: a query parser resolves intent; an A* pathfinder computes the route; a local OllamaClient optionally "
    "drafts instructions.",
    "Grounding: a response generator validates the LLM text against the computed route and falls back to a "
    "deterministic explanation when required.",
    "Interface: a Streamlit web app (Detection, Navigation and Graph tabs) plus an end-to-end NavigationService from "
    "the CLI (main.py).",
]))
B(("h3", "11.2 Stage 1 \u2014 resolution normalisation and chromatic separation"))
B(("p", "Every image is standardised to a configurable maximum working dimension (default 1200 px on the longest "
        "side) with scale factors preserved for reversible coordinate mapping. Because walls are drawn in near-black "
        "ink while door symbols use colour, achromatic separation classifies a pixel as structural if "
        "max(R,G,B) \u2212 min(R,G,B) \u2264 28 and intensity \u2264 175 (workable ranges 20\u201340 and "
        "140\u2013190)."))
B(("h3", "11.3 Stage 2 \u2014 typographic text-artifact suppression"))
B(("p", "Printed labels otherwise binarise as clusters of bogus short walls that shatter rooms. Connected components "
        "of the wall mask are purged when their bounding-box side spans 0.006\u20130.08 of the working dimension, "
        "fill ratio lies in 0.25\u20130.85, area ratio is at most 0.0015, and they show no contact with the "
        "continuous wall skeleton. This mechanism lets one default configuration parse both a 5-room apartment and a "
        "dense 33-unit mall."))
B(("h3", "11.4 Stage 3 \u2014 candidate-driven adaptive morphological gap closing"))
B(("p", "Closing must seal scanning breaks but not genuine doorways. MapMind tests six candidate gap ratios "
        "\u03b3 \u2208 {0.030, 0.040, 0.050, 0.060, 0.075, 0.090}, runs morphological closing for each and "
        "automatically selects the ratio maximising the yield of valid enclosed regions \u2014 removing brittle "
        "per-plan parameter tuning."))
B(("h3", "11.5 Stage 4 \u2014 wall extraction and collinear merging"))
B(("p", "A Canny edge map of the closed mask feeds a Probabilistic Hough transform. Hundreds of collinear fragments "
        "are merged by greedy clustering (angular difference \u2264 7.5\u00b0, endpoint separation \u2264 0.012 of "
        "the working dimension), and a support test discards phantom lines by requiring \u2265 52% of a candidate "
        "wall's pixels to lie on verified wall mass."))
B(("h3", "11.6 Stage 5 \u2014 room and corridor segmentation"))
B(("p", "The free-space mask (inverse of the closed wall mask) is decomposed with 8-connectivity. Border-touching "
        "components are exterior; internal components below 0.004 of the image area or thinner than 0.022 of the "
        "working dimension are rejected. A region becomes a corridor when its aspect ratio \u2265 4.0, minimum "
        "dimension \u2264 0.16 of image size and solidity \u2265 0.20; all other enclosed regions become rooms."))
B(("h3", "11.7 Stage 6 \u2014 dual-source door detection with orthogonal ray probing"))
B(("p", "Door candidates are generated from two independent sources and unioned: (a) chromatic door symbols via "
        "targeted colour filtering (BGR \u2248 (173,130,176), tolerance 30); and (b) region-gap candidates, where "
        "dilated masks of adjacent rooms intersect pairwise to expose boundary openings. Candidates with centroids "
        "closer than 5.5% of image size are de-duplicated, and each surviving door is associated with its two parent "
        "rooms by orthogonal ray probing: horizontal/vertical rays cast up to 10% of the image dimension record the "
        "first distinct region label on each side, and the probe axis yielding two distinct regions at minimal "
        "aggregate centroid-to-door distance fixes the door's orientation and connectivity."))
B(("h3", "11.8 Stage 7 \u2014 navigation graph synthesis with door-aware edge weights"))
B(("p", "Rooms and corridors become graph vertices at their centroids; every confirmed doorway adds an undirected "
        "edge. Unlike hop-count or naive centroid-distance graphs, the edge weight models the true walking distance: "
        "\u03c9(u, v) = ||c(u) \u2212 c(d)|| + ||c(d) \u2212 c(v)||, so traversal costs reflect walking through "
        "the physical door opening."))
B(("h3", "11.9 Stage 8 \u2014 door-centre-aware A* path planning"))
B(("p", "Routes are computed with A* using an admissible, consistent Euclidean centroid-distance heuristic, giving "
        "provably optimal paths. Isolated regions (e.g., a unit with no detected door) yield a clear \u2018not "
        "navigable\u2019 result rather than a bogus route."))
B(("h3", "11.10 Stage 9 \u2014 natural-language query understanding"))
B(("p", "A regular-expression and keyword parser classifies each query into one of four intents \u2014 navigate, "
        "where_is, how_many and clarification_needed \u2014 and normalises slot spellings (\u2018room 101\u2019, "
        "\u2018room1\u2019, \u2018the corridor\u2019) against the live topological inventory, with an optional LLM "
        "fallback for parsing."))
B(("h3", "11.11 Stage 10 \u2014 grounded local LLM explanation with guardrails"))
B(("p", "When conversational instructions are requested, the verified route and room inventory are injected into the "
        "system prompt of a locally hosted Ollama model (default qwen3.5:4b; runtime-switchable without restart). A "
        "post-generation verifier rejects LLM text introducing rooms/doors outside the route or turn directions "
        "unsupported by graph geometry, and substitutes a deterministic rule-based explanation. Every non-LLM "
        "function works without Ollama, so the navigation core is deterministic."))
B(("h3", "11.12 Stage 11 \u2014 interactive user interface"))
B(("p", "A Streamlit 1.38 web app presents Detection, Navigation and Graph tabs; users load a built-in demo plan or "
        "upload their own PNG/JPG/JPEG up to 20 MB. A CLI (main.py) exposes the same features with a --no-llm "
        "deterministic mode."))
B(("h3", "11.13 Implementation stack"))
B(("p", "Python 3.12; OpenCV 4.x; NetworkX 3.3; Pydantic; Streamlit 1.38; Ollama HTTP client (local LLM, no cloud "
        "APIs); pytesseract hook (optional OCR, disabled by default); pytest (117-test suite); matplotlib."))
B(("h3", "11.14 Working examples (internal test evidence, not independent validation)"))
B(("table", {
    "header": ["Benchmark plan", "Image size", "Observed internal result"],
    "rows": [
        ["Sample plan (synthetic academic baseline)", "600 \u00d7 400 px",
         "5 rooms + 1 corridor extracted; navigation query \u2018from Reception to Room 104\u2019 answered with "
         "correct path, doors and cost."],
        ["Apartment plan (real residential layout)", "800 \u00d7 600 px",
         "6 rooms + 1 corridor extracted; full route and door-aware trajectory overlay rendered."],
        ["Commercial mall plan (real, dense)", "650 \u00d7 904 px",
         "33 units, 118 verified walls and 38 functional doors extracted in about 2.0 s on CPU; only one unit "
         "(Room_26, flush gate without swing clearance) remained isolated. Before the robustness fixes the same plan "
         "fragmented into 5 distorted rooms with 138 spurious wall segments."],
    ],
}))
B(("pi", "All three plans were exercised by the project's automated regression suite (117 tests; 117 passed in "
         "55.61 s on CPU), covering preprocessing, coordinate transformation, Hough merging, adaptive closing, "
         "door-pair uniqueness, graph consistency, A* optimality, query parsing and grounding rejection. These are "
         "internal developer tests; no ground-truth benchmark or third-party evaluation has been conducted."))

B(("h2", "12. Attachments: drawings, reports, papers, charts or other materials that may aid in the description"))
B(("p", "The following materials (generated by the MapMind project and supplied with this disclosure) are attached "
        "as Annexures A\u2013H at the end of this document:"))
B(("bullets", [
    "Annexure A \u2014 Fig. 1: MapMind system architecture (raster floor plan \u2192 CV parsing \u2192 topological "
    "graph \u2192 grounded LLM query resolution \u2192 door-aware trajectory rendering).",
    "Annexure B \u2014 Fig. 2: full CV pipeline walkthrough on the apartment plan, stage by stage (input raster, "
    "threshold mask, gap closing, Hough walls, room/corridor segmentation, doors, final annotated plan).",
    "Annexure C \u2014 Fig. 3: full CV pipeline walkthrough on the office plan.",
    "Annexure D \u2014 Fig. 4: full CV pipeline walkthrough on the sample plan.",
    "Annexure E \u2014 Fig. 5: dual-panel (spatial + topological) navigation graphs for the sample, apartment and "
    "office plans.",
    "Annexure F \u2014 Fig. 6: feature-level close-ups (door symbols, stairwell walls, thin corridor walls, room "
    "boundaries) demonstrating detection detail.",
    "Annexure G \u2014 Fig. 7: generalisation comparison across sample, apartment and mall plans (units, walls, "
    "doors, latency), and Fig. 8: quantitative before/after results panel for the mall plan.",
    "Annexure H \u2014 the full IEEE-style technical report (MapMind_IEEE_Paper.pdf), the application source code, "
    "and JSON artifacts (data/processed/floorplan.json and navigation_graph.json) demonstrating machine-readable "
    "outputs.",
]))
B(("pi", "Note: all figures are actual project outputs/images generated from the pipeline's own data artifacts; none "
         "is an artist's impression."))

B(("h2", "13. What are the aspects of your disclosure that you want to claim/monopolise?"))
B(("p", "Proposed Claims \u2014 the following features are proposed for protection. The claims below are an "
        "applicant's draft intended for professional claims-drafting; they do not guarantee patentability."))
B(("p", "1. A computer-implemented system for automatically converting an unannotated two-dimensional raster "
        "floor-plan image into navigable indoor guidance, the system characterised in that it comprises: a "
        "deterministic classical computer-vision extraction module that detects walls, enclosed rooms, corridors "
        "and doorways directly from the raster image using adaptive chromatic separation, typographic text-artifact "
        "suppression, candidate-driven morphological gap closing, Hough-transform line merging with support "
        "validation and connected-component spatial segmentation, without requiring training data, ground-truth "
        "annotation or GPU acceleration; a dual-source doorway detection module that generates door candidates both "
        "from colour-encoded architectural door symbols and from region-gap analysis of adjacent free-space "
        "boundaries, and associates each doorway to its two parent regions by casting orthogonal probe rays; a "
        "topological graph module that constructs an undirected weighted navigation graph in which rooms and "
        "corridors are vertices and doorways are edges whose weights are computed as the sum of Euclidean distances "
        "between a region centroid, the door centre and the other region centroid; a door-centre-aware A* path-"
        "planning module; and a query interface coupled to a locally hosted large language model runtime together "
        "with a deterministic grounding-verification module that rejects ungrounded model output and substitutes "
        "rule-based route-faithful instructions."))
B(("p", "2. The system as claimed in claim 1, wherein the computer-vision module normalises the input image to a "
        "configurable maximum working dimension (default 1200 pixels), and separates structural wall ink from "
        "chromatic door symbols by classifying a pixel as structural when its channel spread is at most a "
        "predetermined achromatic threshold (workable range 20\u201340, default 28) and its intensity is below a "
        "wall cut-off value (workable range 140\u2013190, default 175)."))
B(("p", "3. The system as claimed in claim 1, wherein the text-artifact suppression module discards connected "
        "components whose bounding-box side lies between about 0.006 and 0.08 of the working image dimension, whose "
        "fill ratio lies between 0.25 and 0.85 and whose area ratio does not exceed 0.0015, unless the component "
        "structurally contacts the continuous wall skeleton, whereby printed labels cease to be misread as walls."))
B(("p", "4. The system as claimed in claim 1, wherein the morphological gap-closing step evaluates a ranked set of "
        "candidate gap ratios (workable range 0.03\u20130.09 of the image dimension, e.g., {0.030, 0.040, 0.050, "
        "0.060, 0.075, 0.090}) and automatically selects the ratio that maximises the number of geometrically valid "
        "enclosed regions, whereby one configuration adapts from small apartments to densely packed mall plans "
        "without per-plan tuning."))
B(("p", "5. The system as claimed in claim 1, wherein the dual-source doorway module generates a first class of "
        "candidates by colour-filtering door symbols and a second class by intersecting dilated masks of adjacent "
        "rooms to expose boundary openings, merges duplicate candidates within a centroid distance of at most 5.5% "
        "of image size, and applies geometric size bounds to reject implausible candidates."))
B(("p", "6. The system as claimed in claim 1, wherein the door-to-region association employs orthogonal ray probing "
        "in which horizontal and vertical rays are cast up to about 10% of the image dimension and the probe axis "
        "yielding two distinct regions at the minimal aggregate centroid-to-door distance is selected as the door's "
        "orientation and connectivity."))
B(("p", "7. The system as claimed in claim 1, wherein each graph edge between regions u and v joined by doorway d is "
        "assigned the traversal cost \u03c9(u, v) = ||c(u) - c(d)|| + ||c(d) - c(v)||, and "
        "the A* planner uses a Euclidean centroid-distance heuristic that is admissible and consistent, whereby the "
        "computed route and its rendered polyline pass through door centres rather than clipping walls."))
B(("p", "8. A method for enabling natural-language indoor navigation from an unannotated raster floor-plan image, "
        "the method comprising:"))
B(("p", "a. normalising the image to a working resolution and applying adaptive achromatic/chromatic separation to "
        "derive a structural wall mask and a colour-symbol mask;"))
B(("p", "b. suppressing typographic artifacts and adaptively closing wall gaps from a candidate set of closing "
        "kernels;"))
B(("p", "c. extracting merged wall line segments and segmenting enclosed free space into rooms and corridors;"))
B(("p", "d. detecting doorways via dual-source (colour-symbol and region-gap) candidate generation and associating "
        "each doorway with two parent regions by orthogonal ray probing;"))
B(("p", "e. constructing an undirected weighted topological graph whose edge weights equal the centroid-to-door-"
        "centroid path length;"))
B(("p", "f. parsing a natural-language user query into an intent with source and destination slots resolved against "
        "the Graph inventory;"))
B(("p", "g. computing an optimal route with door-centre-aware A* search; and"))
B(("p", "h. generating a natural-language itinerary using a locally hosted LLM and verifying the output against the "
        "computed route before presentation."))
B(("p", "9. The method as claimed in claim 8, wherein step (h) comprises validating that the generated text "
        "references only rooms and doorways present in the computed route and asserts no directional turns "
        "unsupported by graph geometry, and, upon failure of said validation, substituting a deterministic "
        "instruction text derived from the graph, whereby ungrounded LLM output can never reach the user."))
B(("p", "10. The method as claimed in claim 8, wherein every step from (a) to (g) executes entirely on a local "
        "commodity-CPU processor without network connectivity, and the LLM of step (h) runs on a locally hosted "
        "Ollama runtime so that neither the floor plan nor the user query is transmitted to any external server."))
B(("pi", "Legal note: patentability (novelty, inventive step, industrial applicability, software-claimable subject "
         "matter in the chosen jurisdiction) must be assessed by a patent attorney after a formal prior-art search; "
         "the above claims are not legal advice."))

B(("h2", "14. Novelty/inventiveness search conducted?"))
B(("p", "A formal patent-database novelty search has not yet been conducted. What has been performed, during "
        "preparation of the attached technical report, is a structured literature/prior-art review using public "
        "sources (IEEE Xplore, Google Scholar, ICCV/SCIA/DAS/ICRA proceedings and public open-source repositories):"))
B(("bullets", [
    "Beacon/UWB/Wi-Fi positioning surveys confirm sensor infrastructures carry hardware and calibration cost "
    "[1], [2].",
    "Deep-learning floor-plan parsers (CubiCasa5K, Raster-to-Vector) require large labelled corpora and GPUs, and "
    "output segmentation masks rather than navigable graphs [3], [7].",
    "Classical heuristic vectorisation exists but does not combine dual-source door detection, adaptive "
    "multi-candidate closing and door-weighted routing [6], [9].",
    "No identified prior work couples a training-free classical CV parser with door-centre-weighted A* routing and "
    "a hallucination-guarded local LLM interface in one fully offline product.",
]))
B(("pi", "Action before filing: a professional novelty search is recommended against Espacenet, WIPO PATENTSCOPE, "
         "USPTO and the Indian Patent Office InPASS database, covering IPC class G06F 30/13 (2D design/floor plans), "
         "G01C 21/00 (navigation), G06T 7/00 (image analysis) and G06F 40/30 / G06N 3/0 (language models)."))

B(("h2", "15. Would a person of \u201caverage\u201d skill in the area have arrived at the invention with knowledge "
         "in the public domain?"))
B(("p", "No \u2014 in the applicants' assessment (to be confirmed by formal search and legal counsel) \u2014 for the "
        "following reasons:"))
B(("bullets", [
    "No single public-domain reference teaches the claimed combination: a training-free deterministic CV parser, a "
    "dual-source door detector with orthogonal ray-probe association, door-centre-aware edge weighting and a "
    "hallucination-guarded local LLM interface, integrated and running offline on a CPU.",
    "Following the mainstream deep-learning path would require annotated datasets and GPU training and would not "
    "yield the deterministic, edge-deployable behaviour achieved here; the classical-CV path alone does not produce "
    "the multi-candidate adaptive closing that reconciles apartments and dense malls under one configuration.",
    "The routing innovation is non-obvious: modelling edge weight as the exact centroid\u2192door\u2192centroid "
    "walk changes which routes are perceived as optimal and eliminates wall-clipping routes.",
    "The grounding-verifier-plus-deterministic-fallback pattern was not found in the surveyed LLM-navigation "
    "literature.",
]))
B(("pi", "This is the applicants' reasoned position only; inventiveness is ultimately a legal determination."))

B(("h2", "16. Broad workable ranges for all parameters involved in the invention"))
B(("p", "All parameters are expressed as ratios of the working image size wherever possible, so identical defaults "
        "apply to small apartments and large malls. Distances within the invention are pixel-based Euclidean "
        "metrics (physical metre conversion requires a scale calibration and is not implemented)."))
B(("table", {
    "header": ["Parameter", "Broad workable range", "Default used in MapMind", "Purpose"],
    "rows": [
        ["Working resolution (max_dimension)", "800\u20131600 px", "1200 px",
         "Bounded latency with consistent spatial kernels"],
        ["Input image format / size", "PNG / JPG / JPEG up to 20 MB", "20 MB cap",
         "Robust web upload handling"],
        ["Achromatic channel spread (achromatic_delta)", "20\u201340", "28",
         "Separate black structural ink from coloured door symbols"],
        ["Wall value cut-off (wall_value_max)", "140\u2013190", "175",
         "Intensity ceiling for structural pixels"],
        ["Adaptive threshold block ratio / C", "0.03\u20130.06 / 5\u201312", "0.045 / 8.0",
         "Adaptive local thresholding of wall ink"],
        ["Gap-closing candidate ratios", "0.03\u20130.09 (6 candidates)", "{0.030, 0.040, 0.050, 0.060, 0.075, 0.090}",
         "Adaptive morphological closing that preserves doorways"],
        ["Text-artifact side span (of max dim)", "0.004\u20130.10", "0.006\u20130.08",
         "Reject printed labels masquerading as walls"],
        ["Text-artifact fill ratio", "0.20\u20130.90", "0.25\u20130.85", "Typographic bounding-box plausibility"],
        ["Wall merge angular tolerance", "5\u201310\u00b0", "7.5\u00b0", "Collinear Hough merge decision"],
        ["Wall merge distance (of max dim)", "0.008\u20130.02", "0.012", "Collinear segment gap bridging"],
        ["Wall support fraction", "0.50\u20130.60", "0.52", "Phantom wall-line rejection"],
        ["Room minimum area ratio",
         "0.002\u20130.01", "0.004", "Discard noise fragments; accept genuine rooms"],
        ["Room minimum dimension ratio",
         "0.015\u20130.03", "0.022", "Reject sliver artifacts"],
        ["Corridor aspect ratio", "3.0\u20136.0", "4.0", "Distinguishes corridors from rooms"],
        ["Corridor max width (of max dim)", "0.10\u20130.25", "0.16", "Corridor classification"],
        ["Door symbol tolerance (BGR)", "20\u201345", "30", "Colour-symbol detection robustness"],
        ["Door centroid dedup distance (of max dim)", "0.03\u20130.08", "0.055", "Merging duplicate door candidates"],
        ["Ray probe max distance (of max dim)", "0.05\u20130.15", "0.10", "Door-to-room associate limit"],
        ["LLM request timeout (Ollama)", "10\u201360 s", "30 s", "Local model responsiveness"],
        ["LLM model selection", "Any locally installed Ollama model", "qwen3.5:4b",
         "Explanation generation; runtime-switchable without restart"],
        ["Processing latency (observed, CPU)", "Commodity laptop CPU, no GPU", "\u22482.0 s (33-unit mall plan)",
         "Inverse of throughput; measured internally only"],
    ],
}))
B(("pi", "Note: measured latency values are internal observations on one commodity machine and not independently "
         "validated; the stated workable ranges are the applicants' tuning knowledge (common general technical sense "
         "of the design), not yet registry-verified against the full parametric space."))

B(("h2", "17. References"))
B(("num", [
    "H. Liu, H. Darabi, P. Banerjee and J. Liu, \u201cSurvey of wireless indoor positioning techniques and "
    "systems,\u201d IEEE Trans. Syst., Man, Cybern. C, vol. 37, no. 6, pp. 1067\u20131080, Nov. 2007.",
    "F. Zafari, A. Gkelias and K. K. Leung, \u201cA survey of indoor localization systems and technologies,\u201d "
    "IEEE Commun. Surveys Tuts., vol. 21, no. 3, pp. 2568\u20132599, 2019.",
    "A. Kalervo, J. Ylioinas, M. H\u00e4iki\u00f6, A. Karhu and J. Kannala, \u201cCubiCasa5K: a dataset and an "
    "improved multi-task model for floorplan image analysis,\u201d Proc. SCIA, 2019, pp. 28\u201340.",
    "J. Huang et al., \u201cA survey on hallucination in large language models,\u201d ACM Computing Surveys, "
    "vol. 57, no. 2, pp. 1\u201337, 2024.",
    "M. Basiri, A. M. Amiri and P. Pelletier, \u201cIndoor navigation assistance for visually impaired people: a "
    "survey,\u201d IEEE Access, vol. 6, pp. 4143\u20134158, 2018.",
    "S. Mac\u00e9, H. Locteau, E. Valveny and S. Tabbone, \u201cA system to detect rooms in architectural floor plan "
    "images,\u201d Proc. IAPR DAS, 2010, pp. 167\u2013174.",
    "C. Liu, J. Wu, P. Kohli and Y. Furukawa, \u201cRaster-to-Vector: revisiting floorplan parsing with end-to-end "
    "vectorization,\u201d Proc. IEEE ICCV, 2017, pp. 2110\u20132118.",
    "P. E. Hart, N. J. Nilsson and B. Raphael, \u201cA formal basis for the heuristic determination of minimum cost "
    "paths,\u201d IEEE Trans. Syst. Sci. Cybern., vol. 4, no. 2, pp. 100\u2013107, 1968.",
    "J. Afzal, C. B. Barber and J. M. O'Kane, \u201cTopological map extraction from architectural floor plans,\u201d "
    "Proc. IEEE ICRA, 2014, pp. 2580\u20132586.",
    "Ollama Foundation, \u201cOllama: get up and running with large language models locally,\u201d GitHub, 2024, "
    "github.com/ollama/ollama.",
    "R. Smith, \u201cAn overview of the Tesseract OCR engine,\u201d Proc. ICDAR, vol. 2, 2007, pp. 629\u2013632.",
    "A. Hagberg, P. Swart and D. S Chult, \u201cExploring network structure, dynamics and function using "
    "NetworkX,\u201d Los Alamos National Laboratory, Tech. Rep. LA-UR-08-05495, 2008.",
]))

# ---- Tail sections copied from the master form template (Applicant Details,
# additional notes/remarks), completed with the information supplied. ----

B(("h1", "Applicant Details"))
B(("h2", "1. Applicant Details (Full Names, Nationality and Addresses)"))
B(("table", {
    "header": ["Field", "Details"],
    "rows": [
        ["Full name", "Dr. Seema Bangareswara Hegde"],
        ["Nationality", "Indian"],
        ["Designation", "Professor, Department of CSE"],
        ["Address", "Global Academy of Technology, Ideal Home Town, R R Nagar, Bengaluru-98"],
        ["Email and phone number", NPS],
    ],
}))
B(("pi", "The applicant details above reproduce the information provided in the master form. Contact details and "
         "any additional applicant(s) (e.g., the institution, or student applicants) must be confirmed before "
         "filing."))

B(("h2", "2. Any additional notes or remarks"))
B(("p",
   "All technical statements in this form are drawn from the supplied MapMind project materials (source code, "
   "README, IEEE-style technical report and internal test results). Internal test outcomes are clearly marked as "
   "internal; no independent validation, ground-truth accuracy figure or guaranteed patentability is asserted."))
B(("bullets", [
    "Inventorship of the student contributor(s) who participated in conception must be finalised (names, "
    "contacts, addresses).",
    "The formal novelty search against patent databases (Espacenet, InPASS, PATENTSCOPE) remains to be performed; "
    "the item-14 survey supports but does not replace it.",
    "No public disclosure has taken place; publication or public demonstration should follow filing.",
    "The work is not a funded project and is not bound by a contractual agreement, per the master form; any change "
    "in funding status must be re-declared.",
]))

# ---- Annexures (embedded figures) ----
B(("pagebreak", None))
B(("h1", "Annexures: Supporting Figures"))
ANNEXURES = [
    ("fig1_architecture", "architecture.png",
     "Annexure A \u2014 Fig. 1. MapMind system architecture: data flow from raw raster floor plan through classical "
     "CV parsing and topological graph synthesis to grounded local-LLM query resolution and door-aware trajectory "
     "rendering."),
    ("fig2_apartment", "idf_apartment_pipeline.png",
     "Annexure B \u2014 Fig. 2. Complete eight-stage CV pipeline walkthrough on the apartment plan: input raster; "
     "wall threshold mask; adaptive candidate-driven gap closing; Hough wall detection; connected-component room "
     "and corridor segmentation; door detection; final annotated floor plan."),
    ("fig3_office", "idf_office_pipeline.png",
     "Annexure C \u2014 Fig. 3. The same eight-stage pipeline generalising to the office plan with identical "
     "default parameters."),
    ("fig4_sample", "idf_sample_pipeline.png",
     "Annexure D \u2014 Fig. 4. The same eight-stage pipeline on the synthetic sample plan (5 rooms + 1 corridor)."),
    ("fig5_navgraphs", "idf_nav_graphs.png",
     "Annexure E \u2014 Fig. 5. Dual-panel navigation graphs for the sample, apartment and office plans: spatial "
     "layout with door-aware routes (left) and topological NetworkX structure (right)."),
    ("fig6_zoom", "idf_detail_zoom.png",
     "Annexure F \u2014 Fig. 6. Feature-level close-ups (nearest-neighbour upscaling): door symbol, stairwell walls, "
     "thin corridor wall lines and room boundaries actually detected from the input raster."),
    ("fig7_multiplan", "multiplan_comparison.png",
     "Annexure G \u2014 Fig. 7. Generalisation across sample, apartment and commercial-mall plans (units, walls, "
     "doors, latency)."),
    ("fig8_results", "results_table.png",
     "Annexure G \u2014 Fig. 8. Quantitative detection results panel (before/after the robustness fixes on the mall "
     "plan)."),
]

# ===========================================================================
# DOCX renderer
# ===========================================================================

from docx import Document
from docx.shared import Pt, Inches, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BODY_FONT = "Calibri"
HEAD_COLOR = RGBColor(0x1F, 0x38, 0x64)
ACCENT = RGBColor(0x2E, 0x51, 0x8E)
GRAY = RGBColor(0x40, 0x40, 0x40)


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def set_text(cell_or_para, text, size=10.5, bold=False, italic=False):
    para = cell_or_para if hasattr(cell_or_para, "add_run") else cell_or_para.paragraphs[0]
    para.text = ""
    run = para.add_run(text)
    run.font.name = BODY_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    return para


def add_rich_runs(para, text, size, bold=False, italic=False):
    """Split text so checkbox glyphs render with a font that has them."""
    segments = []
    cur = ""
    for ch in text:
        if ch in (CHECK_ON, CHECK_OFF):
            if cur:
                segments.append(("t", cur))
            segments.append(("sym", ch))
            cur = ""
        else:
            cur += ch
    if cur:
        segments.append(("t", cur))
    if not segments:
        segments = [("t", text)]
    for kind, seg in segments:
        run = para.add_run(seg)
        run.font.name = "Segoe UI Symbol" if kind == "sym" else BODY_FONT
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        if kind == "t":
            # ensure east-asian mapping matches
            rPr = run._element.get_or_add_rPr()
            rFonts = rPr.find(qn("w:rFonts"))
            if rFonts is None:
                rFonts = OxmlElement("w:rFonts")
                rPr.append(rFonts)
            rFonts.set(qn("w:ascii"), BODY_FONT)
            rFonts.set(qn("w:hAnsi"), BODY_FONT)


def build_docx():
    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Inches(0.9)
        sec.bottom_margin = Inches(0.9)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.15

    # Footer: page numbering
    footer = doc.sections[0].footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run("MapMind \u2014 Invention Disclosure Form    |    Page ")
    run.font.size = Pt(9)
    run.font.color.rgb = GRAY
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    fp._p.append(fld)
    run2 = fp.add_run(" of ")
    run2.font.size = Pt(9)
    run2.font.color.rgb = GRAY
    fld2 = OxmlElement("w:fldSimple")
    fld2.set(qn("w:instr"), "NUMPAGES")
    fp._p.append(fld2)

    def title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.font.name = BODY_FONT
        r.font.size = Pt(20)
        r.font.bold = True
        r.font.color.rgb = HEAD_COLOR

    def subtitle(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(14)
        r = p.add_run(text)
        r.font.name = BODY_FONT
        r.font.size = Pt(12.5)
        r.font.italic = True
        r.font.color.rgb = ACCENT

    def h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = BODY_FONT
        r.font.size = Pt(14)
        r.font.bold = True
        r.font.color.rgb = HEAD_COLOR

    def h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = BODY_FONT
        r.font.size = Pt(12)
        r.font.bold = True
        r.font.color.rgb = ACCENT

    def h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = BODY_FONT
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = GRAY

    def para(text, italic=False):
        p = doc.add_paragraph()
        add_rich_runs(p, text, 10.5, italic=italic)
        return p

    def bullets(items, numbered=False):
        style_name = "List Number" if numbered else "List Bullet"
        for it in items:
            p = doc.add_paragraph(style=style_name)
            p.paragraph_format.space_after = Pt(2)
            add_rich_runs(p, it, 10.5)

    def table(spec):
        rows = spec["rows"]
        header = spec.get("header")
        ncols = 2 if header is None else len(header[0]) if False else len(header)
        widths = spec.get("widths")
        t = doc.add_table(rows=0, cols=ncols)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        if header:
            hr = t.add_row()
            for i, htxt in enumerate(header):
                set_text(hr.cells[i], htxt, size=10.5, bold=True)
                shade(hr.cells[i], "1F3864")
                for run in hr.cells[i].paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            t.rows[0]._tr.get_or_add_trPr().append(_tbl_header_el())
        for r_i, row in enumerate(rows):
            tr = t.add_row()
            for i, ctxt in enumerate(row):
                first_col = i == 0
                set_text(tr.cells[i], ctxt, size=10, bold=first_col)
                if first_col:
                    shade(tr.cells[i], "EEF2F8")
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    if w is not None:
                        row.cells[i].width = Inches(w)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return t

    def checklist(items):
        t = doc.add_table(rows=1, cols=2)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = t.rows[0]
        set_text(hdr.cells[0], "Stage", size=10.5, bold=True)
        set_text(hdr.cells[1], "Selected", size=10.5, bold=True)
        shade(hdr.cells[0], "1F3864")
        shade(hdr.cells[1], "1F3864")
        for run in hdr.cells[0].paragraphs[0].runs + hdr.cells[1].paragraphs[0].runs:
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for stage, chosen in items:
            tr = t.add_row()
            p = tr.cells[0].paragraphs[0]
            p.text = ""
            add_rich_runs(p, stage, 10.5)
            p2 = tr.cells[1].paragraphs[0]
            p2.text = ""
            add_rich_runs(p2, (CHECK_ON + "  Yes") if chosen else (CHECK_OFF + "  No"), 10.5)
        hdr.cells[0].width = Inches(4.0)
        hdr.cells[1].width = Inches(2.2)
        doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def figure(fname, caption, max_w=6.0):
        path = os.path.join(FIG_DIR, fname)
        with PILImage.open(path) as im:
            w, h = im.size
        disp_w = max_w
        disp_h = disp_w * h / w
        if disp_h > 8.0:
            disp_h = 8.0
            disp_w = disp_h * w / h
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(path, width=Inches(disp_w))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rc = cap.add_run(caption)
        rc.font.name = BODY_FONT
        rc.font.size = Pt(9.5)
        rc.font.italic = True
        rc.font.color.rgb = GRAY

    def pagebreak():
        doc.add_page_break()

    for block in BLOCKS:
        kind = block[0]
        if kind == "title":
            title(block[1])
        elif kind == "subtitle":
            subtitle(block[1])
        elif kind == "h1":
            h1(block[1])
        elif kind == "h2":
            h2(block[1])
        elif kind == "h3":
            h3(block[1])
        elif kind == "p":
            para(block[1])
        elif kind == "pi":
            para(block[1], italic=True)
        elif kind == "num":
            bullets(block[1], numbered=True)
        elif kind == "bullets":
            bullets(block[1])
        elif kind == "table":
            table(block[1])
        elif kind == "check":
            checklist(block[1])
        elif kind == "figpair":
            pass
        elif kind == "pagebreak":
            pagebreak()
        elif kind == "spacer":
            doc.add_paragraph()

    # Annexure figures after block loop
    for _, fname, cap in ANNEXURES:
        figure(fname, cap)
        doc.add_paragraph().paragraph_format.space_after = Pt(10)

    props = doc.core_properties
    props.title = "MapMind - Invention Disclosure Form (IDF)"
    props.author = "MapMind project team (to be confirmed)"
    props.subject = "Patent disclosure - Vision-based indoor floor plan navigation using local LLMs"

    doc.save(DOCX_PATH)
    print("DOCX written:", DOCX_PATH)


def _tbl_header_el():
    el = OxmlElement("w:tblHeader")
    return el


# ===========================================================================
# PDF renderer (ReportLab, mirrors the DOCX content)
# ===========================================================================

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
    ListFlowable, ListItem, KeepTogether,
)

FONTS = {
    "Reg": "C:/Windows/Fonts/segoeui.ttf",
    "B": "C:/Windows/Fonts/segoeuib.ttf",
    "I": "C:/Windows/Fonts/segoeuii.ttf",
    "Sym": "C:/Windows/Fonts/seguisym.ttf",
}
try:
    pdfmetrics.registerFont(TTFont("SegoeUI", FONTS["Reg"]))
    pdfmetrics.registerFont(TTFont("SegoeUI-B", FONTS["B"]))
    pdfmetrics.registerFont(TTFont("SegoeUI-I", FONTS["I"]))
    pdfmetrics.registerFont(TTFont("SegoeUISym", FONTS["Sym"]))
    PDF_FONT = "SegoeUI"
    PDF_OK = True
except Exception:
    PDF_FONT = "Helvetica"
    PDF_OK = False

C_HEAD = colors.HexColor("#1F3864")
C_ACCENT = colors.HexColor("#2E518E")
C_ROW = colors.HexColor("#EEF2F8")


def symfix(text):
    if not PDF_OK:
        return text.replace(CHECK_ON, "[X]").replace(CHECK_OFF, "[ ]")
    return (text.replace(CHECK_ON, f'<font name="SegoeUISym">{CHECK_ON}</font>')
                .replace(CHECK_OFF, f'<font name="SegoeUISym">{CHECK_OFF}</font>'))


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class PDFNumberedCanvas:
    pass  # replaced by onPage footer


def build_pdf():
    styles = {}
    st = lambda name, **kw: styles.setdefault(name, ParagraphStyle(name, **kw))
    st("title", fontSize=19, leading=24, alignment=TA_CENTER, textColor=C_HEAD,
       fontName=PDF_FONT + "-B" if PDF_OK else "Helvetica-Bold", spaceAfter=6)
    st("subtitle", fontSize=11.5, leading=15, alignment=TA_CENTER, textColor=C_ACCENT,
       fontName=PDF_FONT + "-I" if PDF_OK else "Helvetica-Oblique", spaceAfter=12)
    st("h1", fontSize=13, leading=17, textColor=C_HEAD,
       fontName=PDF_FONT + "-B" if PDF_OK else "Helvetica-Bold", spaceBefore=14, spaceAfter=5)
    st("h2", fontSize=11, leading=14.5, textColor=C_ACCENT,
       fontName=PDF_FONT + "-B" if PDF_OK else "Helvetica-Bold", spaceBefore=9, spaceAfter=3)
    st("h3", fontSize=10, leading=13.5, textColor=colors.HexColor("#404040"),
       fontName=PDF_FONT + "-B" if PDF_OK else "Helvetica-Bold", spaceBefore=7, spaceAfter=2)
    st("p", fontSize=9.5, leading=13, spaceAfter=5)
    st("pi", fontSize=9.5, leading=13, spaceAfter=5, fontName=PDF_FONT + "-I" if PDF_OK else "Helvetica-Oblique",
       textColor=colors.HexColor("#333333"))
    st("cell", fontSize=8.8, leading=11.5)
    st("cellH", fontSize=9.2, leading=11.5, fontName=PDF_FONT + "-B" if PDF_OK else "Helvetica-Bold",
       textColor=colors.white)
    st("cellB", fontSize=8.8, leading=11.5, fontName=PDF_FONT + "-B" if PDF_OK else "Helvetica-Bold")
    st("cap", fontSize=8.5, leading=11, alignment=TA_CENTER, fontName=PDF_FONT + "-I" if PDF_OK else
       "Helvetica-Oblique", textColor=colors.HexColor("#404040"), spaceAfter=10)

    doc = SimpleDocTemplate(
        PDF_PATH, pagesize=A4,
        leftMargin=0.9 * inch, rightMargin=0.9 * inch, topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title="MapMind - Invention Disclosure Form (IDF)", author="MapMind project team")

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(PDF_FONT, 8.5)
        canvas.setFillColor(colors.HexColor("#404040"))
        w = A4[0]
        canvas.drawString(0.9 * inch, 0.5 * inch, "MapMind \u2014 Invention Disclosure Form")
        canvas.drawRightString(w - 0.9 * inch, 0.5 * inch, f"Page {doc_.page}")
        canvas.setStrokeColor(C_ROW)
        canvas.line(0.9 * inch, 0.62 * inch, w - 0.9 * inch, 0.62 * inch)
        canvas.restoreState()

    story = []
    avail_w = A4[0] - 1.8 * inch

    def P(text, sname):
        story.append(Paragraph(symfix(esc(text)), styles[sname]))

    def LIST(items, numbered):
        bf = '1' if numbered else 'bullet'
        lf = ListFlowable(
            [ListItem(Paragraph(symfix(esc(it)), styles["p"]), leftIndent=16) for it in items],
            bulletType=bf, start="1", bulletFontSize=9, leftIndent=14)
        story.append(lf)

    def TABLE(spec):
        rows = spec["rows"]
        header = spec.get("header")
        ncols = len(header) if header else 2
        widths = spec.get("widths")
        data = []
        if header:
            data.append([Paragraph(symfix(esc(h)), styles["cellH"]) for h in header])
        for row in rows:
            data.append([Paragraph(symfix(esc(c)), styles["cellB" if i == 0 else "cell"])
                         for i, c in enumerate(row)])
        col_widths = None
        if widths:
            col_widths = [w * inch if w else None for w in widths]
        if col_widths is None or None in (col_widths or []):
            # distribute: first col narrower when 2 cols (label/value tables)
            if ncols == 2:
                col_widths = [0.32, 0.68]
            elif ncols == 4:
                col_widths = [0.24, 0.22, 0.20, 0.34]
            else:
                col_widths = [1.0 / ncols] * ncols
            col_widths = [x * avail_w for x in col_widths]
        else:
            scale = avail_w / sum(col_widths)
            col_widths = [w * scale for w in col_widths]
        tstyle = [("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9AA6B7")),
                  ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                  ("TOPPADDING", (0, 0), (-1, -1), 4),
                  ("LEFTPADDING", (0, 0), (-1, -1), 5),
                  ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
        if header:
            tstyle.append(("BACKGROUND", (0, 0), (-1, 0), C_HEAD))
            for r in range(1, len(data)):
                tstyle.append(("BACKGROUND", (0, r), (0, r), C_ROW))
        t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0, style=TableStyle(tstyle))
        story.append(t)
        story.append(Spacer(1, 8))

    def CHECK(items):
        data = [[Paragraph("Stage", styles["cellH"]), Paragraph("Selected", styles["cellH"])]]
        for stage, chosen in items:
            data.append([Paragraph(esc(stage), styles["cellB"]),
                         Paragraph(symfix((CHECK_ON + "  Yes") if chosen else (CHECK_OFF + "  No")),
                                   styles["cellB" if chosen else "cell"])])
        col_w = [0.55 * avail_w, 0.45 * avail_w]
        t = Table(data, colWidths=col_w, style=TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9AA6B7")),
            ("BACKGROUND", (0, 0), (-1, 0), C_HEAD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 8))

    for block in BLOCKS:
        kind = block[0]
        if kind == "title":
            story.append(Paragraph(symfix(esc(block[1])), styles["title"]))
        elif kind == "subtitle":
            story.append(Paragraph(symfix(esc(block[1])), styles["subtitle"]))
        elif kind == "h1":
            story.append(Paragraph(symfix(esc(block[1])), styles["h1"]))
        elif kind == "h2":
            story.append(Paragraph(symfix(esc(block[1])), styles["h2"]))
        elif kind == "h3":
            story.append(Paragraph(symfix(esc(block[1])), styles["h3"]))
        elif kind == "p":
            P(block[1], "p")
        elif kind == "pi":
            P(block[1], "pi")
        elif kind == "num":
            LIST(block[1], numbered=True)
        elif kind == "bullets":
            LIST(block[1], numbered=False)
        elif kind == "table":
            TABLE(block[1])
        elif kind == "check":
            CHECK(block[1])
        elif kind == "pagebreak":
            story.append(PageBreak())

    # Annexure figures
    story.append(Paragraph(esc("Annexure A \u2013 F: Supporting Figures"), styles["h1"]))
    for _, fname, cap in ANNEXURES:
        path = os.path.join(FIG_DIR, fname)
        with PILImage.open(path) as im:
            w, h = im.size
        disp_w = 5.9 * inch
        disp_h = disp_w * h / w
        if disp_h > 7.3 * inch:
            disp_h = 7.3 * inch
            disp_w = disp_h * w / h
        img = Image(path, width=disp_w, height=disp_h)
        story.append(KeepTogether([img, Paragraph(esc(cap), styles["cap"])]))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("PDF written:", PDF_PATH)


if __name__ == "__main__":
    build_docx()
    build_pdf()
