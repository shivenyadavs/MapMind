import os
import shutil
from pathlib import Path
from cv.coordinates import scale_floorplan_to_source
from cv.preprocessing import generate_synthetic_floorplan, load_floorplan, save_image
from cv.floorplan_parser import parse_floorplan
from cv.visualization import visualize_floorplan

# Optional mirror directory for IDEs/tools. Set MAPMIND_ARTIFACT_DIR to enable.
_artifact_env = os.getenv("MAPMIND_ARTIFACT_DIR")
ARTIFACT_DIR = Path(_artifact_env) if _artifact_env else None

def main():
    # 1. Regenerate synthetic floor plan
    sample_path = generate_synthetic_floorplan()
    print(f"Generated synthetic floor plan: {sample_path}")

    # 2. Run full CV floor-plan understanding pipeline
    fp = parse_floorplan(sample_path)

    # 3. Create clean annotated visualization in source-image coordinates
    orig = load_floorplan(sample_path)
    fp_source = scale_floorplan_to_source(fp)
    annotated = visualize_floorplan(fp_source, orig)
    out_path = save_image(annotated, "detected_floorplan.png")
    print(f"Annotated image saved to: {out_path}")

    # 4. Copy to artifact directory for convenient display (optional)
    if ARTIFACT_DIR is not None and ARTIFACT_DIR.exists():
        shutil.copy(out_path, ARTIFACT_DIR / "detected_floorplan.png")
        shutil.copy(out_path.parent / "rooms_debug.png", ARTIFACT_DIR / "rooms_debug.png")
        shutil.copy(out_path.parent / "doors_debug.png", ARTIFACT_DIR / "doors_debug.png")
        shutil.copy(out_path.parent / "walls_debug.png", ARTIFACT_DIR / "walls_debug.png")
        shutil.copy(out_path.parent / "corridors_debug.png", ARTIFACT_DIR / "corridors_debug.png")

    return fp

if __name__ == "__main__":
    main()
