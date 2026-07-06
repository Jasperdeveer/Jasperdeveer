"""
Color Naming - Intelligent color name generation
Generates Dutch color names based on HSV analysis
"""

import colorsys
from typing import Tuple


def get_color_name(r: int, g: int, b: int) -> str:
    """
    Generate intelligent Dutch color name from RGB values

    Args:
        r, g, b: RGB values (0-255)

    Returns:
        Dutch color name like "Donkerrood", "Lichtblauw", etc.
    """
    # Convert to HSV
    h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)

    # Convert hue to degrees (0-360)
    hue = h * 360
    saturation = s * 100
    value = v * 100

    # Check for grayscale first
    if saturation < 10:
        if value < 20:
            return "Zwart"
        elif value < 40:
            return "Donkergrijs"
        elif value < 60:
            return "Grijs"
        elif value < 80:
            return "Lichtgrijs"
        else:
            return "Wit"

    # Determine base color by hue
    base_color = _get_base_color(hue)

    # Determine lightness prefix
    if value < 30:
        prefix = "Zeer donker"
    elif value < 50:
        prefix = "Donker"
    elif value < 70:
        prefix = ""
    elif value < 85:
        prefix = "Licht"
    else:
        prefix = "Zeer licht"

    # Adjust for low saturation (pastel colors)
    if saturation < 30:
        if prefix:
            prefix = "Bleek" + prefix.lower()
        else:
            prefix = "Bleek"

    # Combine prefix and base color
    if prefix:
        return f"{prefix}{base_color.lower()}"
    else:
        return base_color


def _get_base_color(hue: float) -> str:
    """
    Get base color name from hue (0-360 degrees)

    Color wheel segments:
    0-15: Rood
    15-45: Oranje
    45-70: Geel
    70-150: Groen
    150-200: Cyaan
    200-260: Blauw
    260-290: Paars
    290-330: Magenta
    330-360: Rood
    """
    if hue < 15 or hue >= 345:
        return "rood"
    elif hue < 35:
        return "oranje"
    elif hue < 70:
        return "geel"
    elif hue < 80:
        return "geelgroen"
    elif hue < 150:
        return "groen"
    elif hue < 180:
        return "groenblauw"
    elif hue < 200:
        return "cyaan"
    elif hue < 260:
        return "blauw"
    elif hue < 290:
        return "paars"
    elif hue < 310:
        return "magenta"
    elif hue < 330:
        return "roze"
    else:
        return "rood"


def calculate_color_distance(r1: int, g1: int, b1: int, r2: int, g2: int, b2: int) -> float:
    """
    Calculate perceptual distance between two RGB colors
    Uses weighted Euclidean distance (more accurate than simple RGB distance)

    Returns:
        Distance value (0 = identical, ~764 = maximum difference)
    """
    # Weighted RGB distance (more perceptually accurate)
    # Weights: R=0.30, G=0.59, B=0.11 (based on human perception)
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2

    return ((2 + (r1 + r2) / 512) * dr * dr +
            4 * dg * dg +
            (2 + (767 - r1 - r2) / 512) * db * db) ** 0.5


def are_colors_similar(r1: int, g1: int, b1: int, r2: int, g2: int, b2: int, threshold: float = 30) -> bool:
    """
    Check if two colors are perceptually similar

    Args:
        r1, g1, b1: First RGB color
        r2, g2, b2: Second RGB color
        threshold: Distance threshold (default 30, range ~0-764)

    Returns:
        True if colors are similar, False otherwise
    """
    distance = calculate_color_distance(r1, g1, b1, r2, g2, b2)
    return distance < threshold
