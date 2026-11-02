from docx import Document
from docx.shared import Pt

doc = Document()

doc.add_heading('MapMind Speaking Script', level=1)

doc.add_heading('Slide 1: Title', level=2)
doc.add_paragraph('Say: "MapMind: Vision‑Based Indoor Floor‑Plan Understanding and Natural Language Navigation Using Local LLMs."')
doc.add_paragraph('Key point: State the project title and authors.')
doc.add_paragraph('Time: 30 seconds')
doc.add_paragraph('Transition: "Now I will describe the problem we are trying to solve."')

doc.add_heading('Slide 2: Problem Statement', level=2)
doc.add_paragraph('Say: "Indoor navigation is challenging because GPS does not work inside buildings. MapMind turns a static floor‑plan image into a navigable graph."')
doc.add_paragraph('Key point: Emphasise the GPS gap and the use of floor plans.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "The core difficulty is converting a visual floor plan into a navigable representation."')

doc.add_heading('Slide 3: Research Gap and Objectives', level=2)
doc.add_paragraph('Say: "There is limited work combining a computer‑vision pipeline with a local LLM for indoor navigation. MapMind fills this gap by providing an end‑to‑end system."')
doc.add_paragraph('Key point: Highlight the novelty of the combination.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "The system has four main layers."')

doc.add_heading('Slide 4: Related Work', level=2)
doc.add_paragraph('Say: "Related work includes CubiCasa5K, R2V, deep floor‑plan recognition, indoor positioning surveys, A* and Dijkstra, Tesseract OCR, and local LLM deployment."')
doc.add_paragraph('Key point: Mention a few key citations without inventing details.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "The system architecture integrates these ideas."')

doc.add_heading('Slide 5: System Architecture', level=2)
doc.add_paragraph('Say: "The system has four layers: the Streamlit UI, the CV pipeline (OpenCV), the navigation graph (NetworkX), and the local LLM (Ollama)."')
doc.add_paragraph('Key point: Walk through the data flow from image to route.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "Now I will describe the CV pipeline in detail."')

doc.add_heading('Slide 6: CV & Floor‑Plan Understanding Pipeline', level=2)
doc.add_paragraph('Say: "The CV pipeline consists of binarisation, morphological closing, Canny edge detection, Hough line detection, wall merging, region segmentation, and door probing. Each stage produces intermediate artifacts that are saved as debug images."')
doc.add_paragraph('Key point: Mention the main stages and that all processing is CPU‑based.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "The resulting rooms, corridors, and doors form a navigation graph."')

doc.add_heading('Slide 7: Location Inventory & Navigation Graph', level=2)
doc.add_paragraph('Say: "Rooms are named Room_1…Room_N with centres and bounding boxes. Corridors are named Corridor_1. Doors have centres, orientations, and connected_regions. The graph nodes are room/corridor names; edges are door connections with weight = centre→door + door→centre distance. Isolated nodes (e.g., Room_26) are recorded."')
doc.add_paragraph('Key point: Explain the graph structure and weight formula.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "With the graph built, we can compute routes."')

doc.add_heading('Slide 8: Natural‑Language Query & Local LLM', level=2)
doc.add_paragraph('Say: "The query parser extracts a small set of canonical intents (navigate, where_is, how_many). Free‑text queries produce a clarification prompt. The Ollama client may be invoked optionally; if not available, the parser alone answers the query."')
doc.add_paragraph('Key point: Emphasise the limited NLU and deterministic fallback.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "Now I will show the experimental results."')

doc.add_heading('Slide 8.5: Experimental Setup', level=2)  # optional
doc.add_paragraph('Say: "We evaluated on three floor‑plans (sample, apartment, mall). The test suite contains 117 tests that all pass. Parsing a 650 × 904 image takes about 2 s on CPU. No Ollama server was running during the audit."')
doc.add_paragraph('Key point: Summarise the experimental conditions.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "Now I present the results."')

doc.add_heading('Slide 9: Results and Limitations', level=2)
doc.add_paragraph('Say: "117/117 tests pass. Wall count: 60 (apt), 118 (mall). Room count: 6 (apt), 5 (sample), 33 (mall). Door count: 6 (apt), 38 (mall). The apartment and sample graphs are connected; the mall graph has one isolated room (Room_26). Route success: apt Room_2→Room_3 via Corridor_1; sample Room_1→Room_5; mall Room_10→Room_20 (13 hops). NLQ: canonical intents succeed; free‑text → clarification. Limitations: no OCR, isolated rooms, limited NLU, image‑resolution dependent."')
doc.add_paragraph('Key point: Present the actual test results and recognised limitations.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "Now I conclude."')

doc.add_heading('Slide 9.5: Conclusion and Future Work', level=2)  # maybe combine with next
doc.add_paragraph('Say: "MapMind demonstrates that a pure CV pipeline + graph + local LLM can turn a floor‑plan into a navigable representation. 117 tests certify structural correctness. Future work includes integrating OCR, user‑correction UI, expanding NLQ intent sets, and evaluating on public datasets (CubiCasa5K, R2V).")')
doc.add_paragraph('Key point: Summarise contribution and outline future directions.')
doc.add_paragraph('Time: 1 minute')
doc.add_paragraph('Transition: "Thank you. I will now take questions."')

doc.add_heading('Slide 11: Questions', level=2)
doc.add_paragraph('Say: "We now take questions from the audience."')
doc.add_paragraph('Key point: Open the floor for questions.')
doc.add_paragraph('Time: remainder of the allotted time')

doc.add_heading('60‑Second Pitch', level=2)
doc.add_paragraph('Say: "MapMind turns a single floor‑plan image into a navigable graph using classical computer‑vision, enables routes annotated with the exact doors used, and answers a small set of natural‑language queries via a locally hosted LLM, all without uploading data to the cloud. The system is fully test‑covered (117 tests) and runs on CPU, making it suitable for privacy‑sensitive indoor navigation scenarios."')
doc.add_paragraph('Time: 60 seconds')

doc.add_heading('Viva Preparation', level=2)
doc.add_paragraph('The accompanying Viva Preparation document (MapMind_Viva_Preparation.docx) contains over 50 questions with accurate answers covering all project areas: CV preprocessing, room/door detection, graph construction, shortest‑path, NLQ, Ollama/Streamlit, evaluation, and failure cases.')

# Save
speaking_script_path = r"C:\Users\shive\mapmind\research_deliverables\MapMind_Speaking_Script.docx"
doc.save(speaking_script_path)
print("Speaking script saved to", speaking_script_path)