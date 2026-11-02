# Research & Academic Deliverables for MapMind

Directory: `C:\Users\shive\mapmind\research_deliverables\`

All research deliverables have been generated, verified, and cross-referenced with the codebase and empirical audit results.

---

## Deliverables Summary Table

| Deliverable File | Format | Size | Description |
|------------------|--------|------|-------------|
| `MapMind_IEEE_Paper.pdf` | PDF | ~1.08 MB | Publication-grade IEEE conference paper (two-column format) generated via ReportLab with 4 high-resolution figures embedded, complete equations, Table I results, and 12 IEEE citations. |
| `MapMind_IEEE_Paper.docx` | DOCX | ~49.4 KB | Full Microsoft Word research paper matching IEEE formatting (Sections I–X). Ready for author name/affiliation customization and journal submission. |
| `ieee_latex/main.tex` | LaTeX | ~32.2 KB | Complete, compilable IEEEtran LaTeX source code (`\documentclass[conference]{IEEEtran}`) incorporating all figures, math formulas, algorithms, Table I, and numbered bibliography. |
| `ieee_latex/figures/` | PNGs | ~790 KB | 4 high-resolution (300 DPI) publication figures: `architecture.png`, `floorplan_detections.png`, `navigation_graph.png`, and `results_table.png`. |
| `MapMind_Project_Presentation.pptx` | PPTX | ~66.6 KB | 12-slide professional 16:9 widescreen presentation deck with verbatim speaker notes embedded directly into every slide's notes frame. |
| `MapMind_Speaking_Script.docx` | DOCX | ~42.5 KB | Slide-by-slide word-for-word presentation script with target time allocations (total ~14 min), core objectives, verbal transition cues, and anticipated examiner questions. |
| `MapMind_Viva_Preparation.docx` | DOCX | ~46.7 KB | Exhaustive viva defense guide containing 40+ technical Q&As across Sections A–N, code implementation citations, a 60-second elevator pitch, and a 2-minute oral defense speech. |
| `CV_Pipeline.pdf` | PDF | ~7.0 KB | 2-page quick-reference technical brief detailing OpenCV parameters, threshold ratios, and edge-handling rules. |

---

## Directory Structure

```text
research_deliverables/
├── CV_Pipeline.pdf
├── MapMind_IEEE_Paper.docx
├── MapMind_IEEE_Paper.pdf
├── MapMind_Project_Presentation.pptx
├── MapMind_Speaking_Script.docx
├── MapMind_Viva_Preparation.docx
├── README_DELIVERABLES.md
└── ieee_latex/
    ├── main.tex
    └── figures/
        ├── architecture.png
        ├── floorplan_detections.png
        ├── navigation_graph.png
        └── results_table.png
```

---

## Verification & Status

1. **Automated Test Suite:** 117 / 117 unit and integration tests passing deterministically (`pytest -q` in ~55s on CPU).
2. **Real Mall Plan Generalization:** 33 store/dining units extracted with 118 structural walls and 38 functional doors.
3. **Local LLM Grounding:** Anti-hallucination verification rejecting invented room IDs and turn commands.
4. **Offline Sovereignty:** 100% on-device CPU execution with zero cloud dependencies.
