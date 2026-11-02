# MapMind Overnight QA Report

Date: 2026-10-26
Scope: CV generalization on a real mall plan, regression checks, navigation/query/LLM grounding audit.

## Summary

The mall parser failure was reproduced and fixed at the segmentation level:

- Isolated printed labels are now removed from the structural wall mask unless they touch a wall, so text such as `Store`/`Restaurant` no longer becomes fake walls.
- Door-closing gap size is now selected adaptively from several candidates. This keeps large apartment rooms and dense mall units working on the same defaults.
- Demo-only aliases (`Reception`, `Room 101`, ...) are no longer applied to larger uploads.
- LLM explanations are rejected and replaced with the deterministic explanation if they mention room/door IDs outside the route or invent left/right turns.
- The app shows a warning for isolated regions and builds upload examples from detected regions instead of demo-only names.

No commit was made. Existing user changes were not overwritten.

## Automated verification

Commands:

```powershell
& "C:\Users\shive\AppData\Local\Programs\Python\Python312\python.exe" -m pytest -q
& "C:\Users\shive\AppData\Local\Programs\Python\Python312\python.exe" -m compileall -q cv graph llm frontend tests run_phase2.py run_phase3.py
```

Result:

- **117 passed in 20.56s**
- `compileall` OK
- Previous baseline: 111 passed in 16.14s

New regression coverage:

- isolated text labels removed; near-wall/door fragments preserved
- adaptive gap chooses the maximum valid region count and respects explicit fixed-gap mode
- demo aliases do not leak into a larger uploaded plan
- hallucinated room IDs and invented turn directions are rejected by the LLM response layer

## Mall plan: before vs after

Input: `C:\Users\shive\Downloads\mall-floor-plan.png` (650 x 904, read-only, outside the repo).

Default parse, before:

- 5 rooms, 1 corridor, 4 doors, 138 walls, 4 connections
- Store regions split into small text-shaped fragments
- Rooms were mostly 70 x 42 text fragments; only Room_4/Room_5/Corridor_1 connected

Default parse, after:

- **33 rooms, 1 corridor, 38 doors, 118 walls, 38 connections**
- Parse time: ~2.0 s
- Rooms now correspond mostly to actual store/restaurant units along the left, right, and central columns
- Graph is **not fully connected**: `Room_26` is isolated (no door detected)
- Wide/L-shaped halls are still classified partly as rooms (`Room_24`, `Room_28`, `Room_30`), not corridors

Visual inspection performed on:

- original mall image
- `walls_debug.png`
- `rooms_debug.png`
- `segmentation_masks_debug.png`
- `doors_debug.png`
- `walls_bin_debug.png`, `closed_walls_debug.png`, `wall_candidates_debug.png`
- store crops

Visual conclusion: the text-artifact walls are gone and the store grid is now mostly recognized. Remaining visible errors are hall classification, a few missed store doors, and duplicate-looking red wall segments. The red segment count (118) is plausible for ~33 units plus doors, so it is not treated as a remaining text-wall bug.

## Regression on existing plans

| Plan | Rooms | Corridors | Doors | Walls | Connections |
|------|------:|----------:|------:|------:|------------:|
| apartment | 6 | 1 | 6 | 60 | 6 |
| office | 5 | 1 | 5 | 15 | 5 |
| sample | 5 | 1 | 6 | 16 | 6 |

- Apartment room/corridor topology is unchanged. Door/connection counts moved from 7/7 to 6/6 because the ambiguous door below `Room_3` now correctly connects `Room_3` to `Corridor_1` instead of `Room_1`, and a false region-gap door is no longer added.
- This also fixes `Room_2 -> Room_3` routing: it now goes `Room_2 -> Corridor_1 -> Room_3` instead of detouring through `Room_1`.
- Office and sample are unchanged.
- The apartment wall count moved from 56 to 60; this is a Hough/merge side effect of the cleaned mask, not a room-topology regression.

## Navigation / query / LLM audit

Verified:

- Sample route: `Room_1 -> Corridor_1 -> Room_3 -> Room_5`, doors `Door_1 -> Door_3 -> Door_5`.
- A* costs still match NetworkX weighted shortest paths (existing test).
- Mall store-to-store routing works for connected regions, e.g. `Room_10 -> Room_20` returns a full path.
- Queries for missing regions fail safely with `clarification_needed` or `error`; no route is fabricated.
- `Reception`/`Room 101` no longer resolve on the mall plan.
- Model selection still uses the selected model; fallback still works (existing tests).

Issues found and left for later:

- Mall route `Room_10 -> Room_20` takes 13 hops through stores/halls. Door topology is connected, but it may not match human walking preference. No corridor-preference policy exists.
- `Room_26` is isolated because its door was not detected.
- No natural-language count or nearest-washroom/restaurant/exit intent. Such queries currently become clarification prompts.
- Grounding check catches invented `Room_N`/`Door_N`/`Corridor_N` and `turn left/right`, but cannot catch free-text inventions such as a store brand name.
- Large/L-shaped halls may be outlined as rooms. This affects route wording, not graph connectivity.

## OCR / labels

No OCR backend is installed (`pytesseract`, `easyocr`, `paddleocr` absent; no Tesseract executable). Windows OCR can read some mall labels only when the image is upscaled 3x, but it is not integrated because it is platform-specific and produced typos. Therefore:

- mall stores/restaurants still appear as `Room_N`
- washroom/restaurant/exit lookup by printed label is not available in this environment
- OCR remains optional and unverified against a real annotated mall

## Automated vs visual evidence

Automated:

- 117 tests, compileall, deterministic region counts, graph node/edge checks

Visual:

- mall wall/room/segmentation/doors/crops inspected
- apartment/office original and annotated images previously inspected

These are reported separately; passing tests do not prove mall visual accuracy.

## Recommended next three fixes

1. Add hall/L-shaped-region classification or a corridor-preference path cost so routes avoid cutting through stores.
2. Improve door recovery for small store units, starting with the isolated `Room_26`.
3. Integrate a verified OCR path (or a user-supplied region-label editor) so washroom/restaurant/exit/store names can be searched without inventing locations.

## Files changed in this pass

- `cv/pipeline_config.py`: adaptive gap candidates, text-artifact thresholds
- `cv/floorplan_parser.py`: text-artifact suppression, adaptive gap selection
- `llm/query_parser.py`: demo-alias scoping, safe start-location hint
- `llm/response_generator.py`: grounding rejection
- `frontend/app.py`: isolated-node warning, dynamic upload examples, wording
- `tests/test_cv_improvements.py`, `tests/test_bugfixes.py`, `tests/test_phase4.py`: regression tests
- `README.md`: configuration, counts, limitations

Known baseline limitations remain: pixel-distance units, optional OCR, single floor only, upload persistence.
