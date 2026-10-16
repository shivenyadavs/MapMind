

import pathlib

import cv2
import numpy as np
import pytest

from cv.preprocessing import (
    load_floorplan,
    resize_image,
    convert_to_grayscale,
    denoise_image,
    threshold_image,
    generate_synthetic_floorplan,
)

# Helpers
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

@pytest.fixture(scope="module")
def sample_image_path():
    # Ensure synthetic image exists
    path = generate_synthetic_floorplan()
    return path

def test_load_floorplan(sample_image_path):
    img = load_floorplan(sample_image_path)
    assert isinstance(img, np.ndarray)
    assert img.ndim == 3  # BGR
    assert img.shape[2] == 3

def test_resize_image(sample_image_path):
    img = load_floorplan(sample_image_path)
    resized = resize_image(img, max_dim=200)
    assert max(resized.shape[:2]) == 200
    # Aspect ratio preserved
    h, w = img.shape[:2]
    rh, rw = resized.shape[:2]
    assert round(rh / rw, 2) == round(h / w, 2)

def test_convert_to_grayscale(sample_image_path):
    img = load_floorplan(sample_image_path)
    gray = convert_to_grayscale(img)
    assert gray.ndim == 2
    assert gray.shape == img.shape[:2]

def test_denoise_and_threshold(sample_image_path):
    img = load_floorplan(sample_image_path)
    gray = convert_to_grayscale(img)
    denoised = denoise_image(gray)
    thresh = threshold_image(denoised, method="otsu")
    assert thresh.ndim == 2
    # Binary image should contain only 0 and 255
    unique_vals = np.unique(thresh)
    assert set(unique_vals.tolist()).issubset({0, 255})

