"""cv/preprocessing.py

Utility functions for the Phase 1 image‑processing pipeline.

Each function operates on a ``numpy.ndarray`` image and returns the processed image.
The pipeline is deliberately broken into small, testable pieces.
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from typing import Optional

from utils.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, DEFAULT_MAX_DIMENSION

__all__ = [
    "load_floorplan",
    "resize_image",
    "convert_to_grayscale",
    "denoise_image",
    "threshold_image",
    "morphological_cleanup",
    "detect_edges",
    "detect_lines",
    "find_contours",
    "save_image",
    "generate_synthetic_floorplan",
    "generate_second_floorplan",
]


def load_floorplan(image_path: Path) -> np.ndarray:
    """Load an image from *image_path*.

    Parameters
    ----------
    image_path: Path
        Path to a PNG/JPG/JPEG image.

    Returns
    -------
    np.ndarray
        BGR image as loaded by OpenCV.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the image cannot be decoded.
    """
    if not image_path.is_file():
        raise FileNotFoundError(f"Floor‑plan image not found: {image_path}")
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")
    return img


def resize_image(image: np.ndarray, max_dim: int = DEFAULT_MAX_DIMENSION) -> np.ndarray:
    """Resize *image* so that its longest side equals ``max_dim`` while keeping aspect ratio.
    """
    height, width = image.shape[:2]
    if max(height, width) <= max_dim:
        return image.copy()
    scale = max_dim / max(height, width)
    new_size = (int(width * scale), int(height * scale))
    resized = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    return resized


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert a BGR image to a single‑channel grayscale image.
    """
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def denoise_image(image: np.ndarray, ksize: int = 5) -> np.ndarray:
    """Apply Gaussian blur to reduce noise.
    """
    # ``ksize`` must be odd and > 1
    if ksize % 2 == 0:
        ksize += 1
    return cv2.GaussianBlur(image, (ksize, ksize), 0)


def threshold_image(image: np.ndarray, method: str = "otsu") -> np.ndarray:
    """Binary threshold using Otsu or adaptive Gaussian.

    Parameters
    ----------
    method: {"otsu", "adaptive"}
    """
    if method == "otsu":
        _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == "adaptive":
        thresh = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )
    else:
        raise ValueError("method must be 'otsu' or 'adaptive'")
    return thresh


def morphological_cleanup(image: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Perform opening followed by closing to clean up the binary image.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    opened = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    return closed


def detect_edges(image: np.ndarray, low: int = 50, high: int = 150) -> np.ndarray:
    """Canny edge detector.
    """
    return cv2.Canny(image, low, high)


def detect_lines(edge_image: np.ndarray, rho: float = 1, theta: float = np.pi / 180, threshold: int = 100) -> np.ndarray:
    """Detect line segments using probabilistic Hough transform.
    Returns an image with lines drawn (BGR) for visualisation.
    """
    lines = cv2.HoughLinesP(edge_image, rho, theta, threshold, minLineLength=30, maxLineGap=10)
    line_img = np.zeros((*edge_image.shape, 3), dtype=np.uint8)
    if lines is not None:
        # lines may have shape (N, 1, 4) or (N, 4)
        lines = lines.reshape(-1, 4)
        for x1, y1, x2, y2 in lines:
            cv2.line(line_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
    return line_img


def find_contours(binary_image: np.ndarray) -> np.ndarray:
    """Find external contours and return an image visualising them.
    """
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contour_img = np.zeros((*binary_image.shape, 3), dtype=np.uint8)
    cv2.drawContours(contour_img, contours, -1, (0, 0, 255), 2)
    return contour_img


def save_image(image: np.ndarray, filename: str, output_dir: Optional[Path] = None) -> Path:
    """Save *image* under *output_dir* (defaults to ``PROCESSED_DATA_DIR``).

    Returns the absolute pathlib.Path of the saved file.
    """
    target_dir = Path(output_dir) if output_dir is not None else PROCESSED_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / filename
    # ``imwrite`` expects a string path; on Windows we must handle Unicode correctly
    success = cv2.imwrite(str(out_path), image)
    if not success:
        raise IOError(f"Failed to write image to {out_path}")
    return out_path


def generate_synthetic_floorplan(
    width: int = 800,
    height: int = 600,
    filename: str = "sample_floorplan.png",
    output_dir: Optional[Path] = None,
) -> Path:
    """Create a clean architectural floor plan suitable for CV detection.

    Layout:
    - Reception at top
    - Central corridor
    - Four rooms (R101, R102, R103, R104) in a 2x2 grid below corridor
    - Clear door openings in wall boundaries
    - Clean white interiors and solid dark walls (thickness 6px)
    """
    wall_thick = 6
    img = np.full((height, width, 3), 255, dtype=np.uint8)  # White canvas

    # Outer perimeter walls (enclosing building envelope)
    cv2.rectangle(img, (100, 60), (700, 540), (0, 0, 0), wall_thick)

    # Interior Wall 1: Separating Reception and Corridor (Y = 210)
    # Door 1 (Reception <-> Corridor) at X in [380, 420]
    cv2.line(img, (100, 210), (380, 210), (0, 0, 0), wall_thick)
    cv2.line(img, (420, 210), (700, 210), (0, 0, 0), wall_thick)

    # Interior Wall 2: Separating Corridor and Upper Rooms R101/R102 (Y = 290)
    # Door 2 (Corridor <-> R101) at X in [230, 270]
    # Door 3 (Corridor <-> R102) at X in [530, 570]
    cv2.line(img, (100, 290), (230, 290), (0, 0, 0), wall_thick)
    cv2.line(img, (270, 290), (530, 290), (0, 0, 0), wall_thick)
    cv2.line(img, (570, 290), (700, 290), (0, 0, 0), wall_thick)

    # Interior Wall 3: Separating Upper Rooms (R101/R102) and Lower Rooms (R103/R104) (Y = 415)
    # Door 4 (R101 <-> R103) at X in [230, 270]
    # Door 5 (R102 <-> R104) at X in [530, 570]
    cv2.line(img, (100, 415), (230, 415), (0, 0, 0), wall_thick)
    cv2.line(img, (270, 415), (530, 415), (0, 0, 0), wall_thick)
    cv2.line(img, (570, 415), (700, 415), (0, 0, 0), wall_thick)

    # Interior Wall 4: Vertical wall dividing Left column (R101, R103) and Right column (R102, R104) (X = 400)
    # Door 6 (R103 <-> R104) at Y in [455, 495]
    cv2.line(img, (400, 290), (400, 455), (0, 0, 0), wall_thick)
    cv2.line(img, (400, 495), (400, 540), (0, 0, 0), wall_thick)

    target_dir = Path(output_dir) if output_dir is not None else RAW_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / filename
    if not cv2.imwrite(str(out_path), img):
        raise IOError(f"Failed to write image to {out_path}")
    return out_path


def generate_second_floorplan(
    width: int = 800,
    height: int = 600,
    filename: str = "office_floorplan.png",
    output_dir: Optional[Path] = None,
) -> Path:
    """Create a second distinct architectural floor plan (L-shaped corridor layout) for validation.
    """
    wall_thick = 6
    img = np.full((height, width, 3), 255, dtype=np.uint8)

    # Outer perimeter (80, 50) to (720, 550)
    cv2.rectangle(img, (80, 50), (720, 550), (0, 0, 0), wall_thick)

    # Horizontal Corridor at Y in [230, 310], spanning across
    # Wall above corridor (Y=230)
    cv2.line(img, (80, 230), (330, 230), (0, 0, 0), wall_thick)  # Door at 330..370
    cv2.line(img, (370, 230), (720, 230), (0, 0, 0), wall_thick)

    # Upper vertical divider at X=400 (Y in 50..230) - divides upper area into Room 1 & Room 2
    cv2.line(img, (400, 50), (400, 120), (0, 0, 0), wall_thick)  # Door at 120..160
    cv2.line(img, (400, 160), (400, 230), (0, 0, 0), wall_thick)

    # Wall below corridor (Y=310)
    cv2.line(img, (80, 310), (250, 310), (0, 0, 0), wall_thick)  # Door at 250..290
    cv2.line(img, (290, 310), (510, 310), (0, 0, 0), wall_thick)  # Door at 510..550
    cv2.line(img, (550, 310), (720, 310), (0, 0, 0), wall_thick)

    # Lower vertical dividers dividing bottom into 3 rooms: X=300 and X=520 (Y in 310..550)
    cv2.line(img, (300, 310), (300, 420), (0, 0, 0), wall_thick)  # Door at 420..460
    cv2.line(img, (300, 460), (300, 550), (0, 0, 0), wall_thick)
    cv2.line(img, (520, 310), (520, 550), (0, 0, 0), wall_thick)

    target_dir = Path(output_dir) if output_dir is not None else RAW_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / filename
    if not cv2.imwrite(str(out_path), img):
        raise IOError(f"Failed to write image to {out_path}")
    return out_path

