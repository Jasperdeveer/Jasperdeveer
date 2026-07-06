"""
Selection Tools - Advanced manual selection for paint-by-numbers
Provides magic wand, brush, and polygon selection tools
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SelectionMode(Enum):
    """Selection tool modes"""
    NONE = "none"
    MAGIC_WAND = "magic_wand"
    BRUSH = "brush"
    POLYGON = "polygon"


class SelectionTools:
    """Manager for selection tools and selection mask"""

    def __init__(self, image_shape: Tuple[int, int]):
        """
        Initialize selection tools

        Args:
            image_shape: (height, width) of the image
        """
        self.height, self.width = image_shape
        self.selection_mask = np.zeros((self.height, self.width), dtype=np.uint8)
        self.mode = SelectionMode.NONE

        # Polygon tool state
        self.polygon_points: List[Tuple[int, int]] = []

        # Brush tool settings
        self.brush_size = 20

        # Magic wand settings
        self.tolerance = 30  # Color difference tolerance

    def clear_selection(self):
        """Clear the selection mask"""
        self.selection_mask = np.zeros((self.height, self.width), dtype=np.uint8)
        logger.info("Selection cleared")

    def get_selection_count(self) -> int:
        """Get number of selected pixels"""
        return np.sum(self.selection_mask > 0)

    def is_selection_active(self) -> bool:
        """Check if there's an active selection"""
        return self.get_selection_count() > 0

    def magic_wand_select(self, image: np.ndarray, x: int, y: int, add_to_selection: bool = False):
        """
        Select region using magic wand (flood fill based on color similarity)

        Args:
            image: RGB image
            x, y: Click coordinates
            add_to_selection: If True, add to existing selection; if False, replace
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            logger.warning(f"Click outside image bounds: ({x}, {y})")
            return

        # Get clicked color
        clicked_color = image[y, x]

        # Create mask for flood fill
        mask = np.zeros((self.height + 2, self.width + 2), dtype=np.uint8)

        # If adding to selection, start with existing mask
        if add_to_selection:
            mask[1:-1, 1:-1] = self.selection_mask
        else:
            self.selection_mask.fill(0)

        # Perform flood fill
        # loDiff and upDiff define color tolerance
        lo_diff = (self.tolerance, self.tolerance, self.tolerance)
        up_diff = (self.tolerance, self.tolerance, self.tolerance)

        flags = 4  # 4-connectivity
        flags |= (255 << 8)  # Fill with 255
        flags |= cv2.FLOODFILL_MASK_ONLY  # Only update mask, not image
        flags |= cv2.FLOODFILL_FIXED_RANGE  # Compare to seed color, not neighboring

        # Make a copy for flood fill
        img_copy = image.copy()

        try:
            cv2.floodFill(img_copy, mask, (x, y), (255, 255, 255), lo_diff, up_diff, flags)

            # Extract the filled region (excluding border)
            filled = mask[1:-1, 1:-1]

            # Update selection mask
            if add_to_selection:
                self.selection_mask = np.maximum(self.selection_mask, filled)
            else:
                self.selection_mask = filled

            count = self.get_selection_count()
            logger.info(f"Magic wand selected {count} pixels at ({x}, {y})")

        except Exception as e:
            logger.error(f"Magic wand error: {e}")

    def brush_select(self, x: int, y: int, add: bool = True):
        """
        Select region using brush

        Args:
            x, y: Brush center coordinates
            add: If True, add to selection; if False, remove from selection
        """
        if not (0 <= x < self.width and 0 <= y < self.height):
            return

        # Draw circle on mask
        value = 255 if add else 0
        cv2.circle(self.selection_mask, (x, y), self.brush_size, value, -1)

    def add_polygon_point(self, x: int, y: int):
        """
        Add a point to the polygon

        Args:
            x, y: Point coordinates
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            self.polygon_points.append((x, y))
            logger.info(f"Added polygon point: ({x}, {y}). Total: {len(self.polygon_points)}")

    def complete_polygon_selection(self, add_to_selection: bool = False):
        """
        Complete the polygon and fill the selection

        Args:
            add_to_selection: If True, add to existing selection; if False, replace
        """
        if len(self.polygon_points) < 3:
            logger.warning("Need at least 3 points to create polygon")
            return

        # Convert points to numpy array
        points = np.array(self.polygon_points, dtype=np.int32)

        # Create temporary mask for this polygon
        temp_mask = np.zeros((self.height, self.width), dtype=np.uint8)

        # Fill polygon
        cv2.fillPoly(temp_mask, [points], 255)

        # Update selection mask
        if add_to_selection:
            self.selection_mask = np.maximum(self.selection_mask, temp_mask)
        else:
            self.selection_mask = temp_mask

        count = self.get_selection_count()
        logger.info(f"Polygon selection complete: {count} pixels selected")

        # Clear polygon points
        self.polygon_points = []

    def cancel_polygon(self):
        """Cancel current polygon selection"""
        self.polygon_points = []
        logger.info("Polygon cancelled")

    def get_visualization_overlay(self, image: np.ndarray, alpha: float = 0.4) -> np.ndarray:
        """
        Get image with selection overlay

        Args:
            image: Original RGB image
            alpha: Overlay transparency (0-1)

        Returns:
            Image with selection overlay
        """
        result = image.copy()

        if not self.is_selection_active():
            return result

        # Create colored overlay for selected regions
        overlay = result.copy()
        overlay[self.selection_mask > 0] = [100, 200, 255]  # Light blue

        # Blend
        result = cv2.addWeighted(result, 1 - alpha, overlay, alpha, 0)

        # Draw outline
        contours, _ = cv2.findContours(self.selection_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(result, contours, -1, (0, 150, 255), 2)

        return result

    def apply_selection_to_color_map(
        self,
        color_map: np.ndarray,
        target_color_index: int
    ) -> np.ndarray:
        """
        Apply the selection to the color map by setting selected pixels to target color

        Args:
            color_map: Color map array (flattened or 2D)
            target_color_index: Index of the color to apply (0-based)

        Returns:
            Updated color map
        """
        if not self.is_selection_active():
            logger.warning("No active selection to apply")
            return color_map

        # Reshape color_map if needed
        if len(color_map.shape) == 1:
            color_map_2d = color_map.reshape(self.height, self.width)
        else:
            color_map_2d = color_map

        # Apply selection
        color_map_2d[self.selection_mask > 0] = target_color_index

        count = self.get_selection_count()
        logger.info(f"Applied selection: {count} pixels set to color {target_color_index}")

        return color_map_2d.flatten() if len(color_map.shape) == 1 else color_map_2d

    def invert_selection(self):
        """Invert the selection mask"""
        self.selection_mask = 255 - self.selection_mask
        logger.info(f"Selection inverted: {self.get_selection_count()} pixels selected")

    def grow_selection(self, pixels: int = 5):
        """
        Grow the selection by specified pixels

        Args:
            pixels: Number of pixels to grow
        """
        if not self.is_selection_active():
            return

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (pixels * 2 + 1, pixels * 2 + 1))
        self.selection_mask = cv2.dilate(self.selection_mask, kernel, iterations=1)

        logger.info(f"Selection grown by {pixels} pixels")

    def shrink_selection(self, pixels: int = 5):
        """
        Shrink the selection by specified pixels

        Args:
            pixels: Number of pixels to shrink
        """
        if not self.is_selection_active():
            return

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (pixels * 2 + 1, pixels * 2 + 1))
        self.selection_mask = cv2.erode(self.selection_mask, kernel, iterations=1)

        logger.info(f"Selection shrunk by {pixels} pixels")
