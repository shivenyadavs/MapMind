import shutil
from pathlib import Path
from cv.preprocessing import generate_synthetic_floorplan, load_floorplan, save_image
from cv.floorplan_parser import parse_floorplan
from cv.visualization import visualize_floorplan

ARTIFACT_DIR = Path(r"C:\Users\shive\.gemini\antigravity-ide\brain\06f8d4de-7323-458f-b65c-4250738f0e40")

def main():
    # 1. Regenerate synthetic floor plan
    sample_path = generate_synthetic_floorplan()
    print(f"Generated synthetic floor plan: {sample_path}")

    # 2. Run full CV floor-plan understanding pipeline
    fp = parse_floorplan(sample_path)

    # 3. Create clean annotated visualization
    orig = load_floorplan(sample_path)
    annotated = visualize_floorplan(fp, orig)
    out_path = save_image(annotated, "detected_floorplan.png")
    print(f"Annotated image saved to: {out_path}")

    # 4. Copy to artifact directory for convenient display
    if ARTIFACT_DIR.exists():
        shutil.copy(out_path, ARTIFACT_DIR / "detected_floorplan.png")
        shutil.copy(out_path.parent / "rooms_debug.png", ARTIFACT_DIR / "rooms_debug.png")
        shutil.copy(out_path.parent / "doors_debug.png", ARTIFACT_DIR / "doors_debug.png")
        shutil.copy(out_path.parent / "walls_debug.png", ARTIFACT_DIR / "walls_debug.png")
        shutil.copy(out_path.parent / "corridors_debug.png", ARTIFACT_DIR / "corridors_debug.png")

    return fp

if __name__ == "__main__":
    main()
