"""
Color Manager - Manages color palette with names and numbers
Converts JavaScript colorManager.js to Python
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Color:
    """Represents a single color with metadata"""

    def __init__(self, r: int, g: int, b: int, number: int, name: str = ""):
        self.r = r
        self.g = g
        self.b = b
        self.number = number
        self.name = name if name else f"Kleur {number}"
        self.id = id(self)  # Unique ID

    def to_rgb_array(self) -> np.ndarray:
        """Return as numpy array [r, g, b]"""
        return np.array([self.r, self.g, self.b], dtype=np.uint8)

    def to_hex(self) -> str:
        """Return as hex string #RRGGBB"""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'number': self.number,
            'r': self.r,
            'g': self.g,
            'b': self.b,
            'hex': self.to_hex(),
            'name': self.name
        }

    def __repr__(self):
        return f"Color({self.number}: {self.name} - {self.to_hex()})"


class ColorManager:
    """Manages color palette for paint-by-numbers"""

    def __init__(self):
        self.colors: List[Color] = []
        self.history: List[List[Color]] = []
        self.preview_color_index: Optional[int] = None
        self.next_number = 1

    def set_colors(self, rgb_colors: np.ndarray) -> None:
        """
        Set colors from numpy array of RGB values

        Args:
            rgb_colors: Array of shape (n, 3) with RGB values
        """
        # Save current state for undo
        if self.colors:
            self.history.append(self.colors.copy())

        self.colors = []
        self.next_number = 1

        for rgb in rgb_colors:
            color = Color(
                r=int(rgb[0]),
                g=int(rgb[1]),
                b=int(rgb[2]),
                number=self.next_number
            )
            self.colors.append(color)
            self.next_number += 1

        logger.info(f"Set {len(self.colors)} colors")

    def add_color(self, r: int, g: int, b: int, name: str = "") -> Color:
        """Add a new color to the palette"""
        # Save for undo
        self.history.append(self.colors.copy())

        color = Color(r, g, b, self.next_number, name)
        self.colors.append(color)
        self.next_number += 1

        logger.info(f"Added color: {color}")
        return color

    def remove_color(self, color_id: int) -> bool:
        """Remove a color by ID"""
        # Save for undo
        self.history.append(self.colors.copy())

        for i, color in enumerate(self.colors):
            if color.id == color_id:
                removed = self.colors.pop(i)
                logger.info(f"Removed color: {removed}")
                return True

        return False

    def update_color(self, color_id: int, r: int, g: int, b: int) -> bool:
        """Update a color's RGB values"""
        # Save for undo
        self.history.append(self.colors.copy())

        for color in self.colors:
            if color.id == color_id:
                color.r = r
                color.g = g
                color.b = b
                logger.info(f"Updated color: {color}")
                return True

        return False

    def rename_color(self, color_id: int, new_name: str) -> bool:
        """Rename a color"""
        for color in self.colors:
            if color.id == color_id:
                color.name = new_name
                logger.info(f"Renamed color to: {new_name}")
                return True

        return False

    def get_colors(self) -> List[Color]:
        """Get all colors"""
        return self.colors

    def get_colors_as_array(self) -> np.ndarray:
        """Get colors as numpy array of shape (n, 3)"""
        if not self.colors:
            return np.array([])

        return np.array([
            [color.r, color.g, color.b]
            for color in self.colors
        ], dtype=np.uint8)

    def get_color_by_index(self, index: int) -> Optional[Color]:
        """Get color by index"""
        if 0 <= index < len(self.colors):
            return self.colors[index]
        return None

    def get_color_by_id(self, color_id: int) -> Optional[Color]:
        """Get color by ID"""
        for color in self.colors:
            if color.id == color_id:
                return color
        return None

    def get_color_count(self) -> int:
        """Get number of colors"""
        return len(self.colors)

    def set_preview_color(self, index: int) -> None:
        """Set preview color index (for highlighting)"""
        if 0 <= index < len(self.colors):
            self.preview_color_index = index
        else:
            self.preview_color_index = None

    def clear_preview(self) -> None:
        """Clear preview color"""
        self.preview_color_index = None

    def is_preview_active(self) -> bool:
        """Check if preview is active"""
        return self.preview_color_index is not None

    def get_preview_color_index(self) -> Optional[int]:
        """Get preview color index"""
        return self.preview_color_index

    def undo(self) -> bool:
        """Undo last change"""
        if not self.history:
            return False

        self.colors = self.history.pop()
        logger.info("Undo applied")
        return True

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return len(self.history) > 0

    def clear(self) -> None:
        """Clear all colors"""
        self.history.append(self.colors.copy())
        self.colors = []
        self.next_number = 1
        logger.info("Cleared all colors")

    def sort_by_brightness(self) -> None:
        """Sort colors by brightness (luminance)"""
        self.history.append(self.colors.copy())

        def brightness(color: Color) -> float:
            # Use perceived brightness formula
            return 0.299 * color.r + 0.587 * color.g + 0.114 * color.b

        self.colors.sort(key=brightness)

        # Renumber after sorting
        for i, color in enumerate(self.colors):
            color.number = i + 1

        logger.info("Sorted colors by brightness")

    def sort_by_hue(self) -> None:
        """Sort colors by hue"""
        self.history.append(self.colors.copy())

        def rgb_to_hsv(color: Color) -> Tuple[float, float, float]:
            r, g, b = color.r / 255.0, color.g / 255.0, color.b / 255.0
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            diff = max_c - min_c

            if diff == 0:
                h = 0
            elif max_c == r:
                h = (60 * ((g - b) / diff) + 360) % 360
            elif max_c == g:
                h = (60 * ((b - r) / diff) + 120) % 360
            else:
                h = (60 * ((r - g) / diff) + 240) % 360

            s = 0 if max_c == 0 else diff / max_c
            v = max_c

            return h, s, v

        self.colors.sort(key=lambda c: rgb_to_hsv(c)[0])

        # Renumber after sorting
        for i, color in enumerate(self.colors):
            color.number = i + 1

        logger.info("Sorted colors by hue")
