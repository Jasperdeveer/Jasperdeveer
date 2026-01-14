"""
Visualizer - Rendering engine for different visualization modes
Converts JavaScript visualization.js to Python with OpenCV/NumPy
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict
import logging

from image_processor import ImageProcessor
from color_manager import ColorManager, Color
from contour_tracer import ContourTracer

logger = logging.getLogger(__name__)


class Visualizer:
    """High-performance visualization with OpenCV"""

    def __init__(self):
        self.image_processor: Optional[ImageProcessor] = None
        self.color_manager: Optional[ColorManager] = None
        self.contour_tracer = ContourTracer()

        self.mode = 'original'  # 'original', 'paintByNumbers', 'lineDrawing'
        self.show_numbers = True

        # Cached data to avoid recomputation
        self.quantized_image: Optional[np.ndarray] = None
        self.color_map: Optional[np.ndarray] = None
        self.contours: Optional[List[np.ndarray]] = None
        self.regions: Optional[List[dict]] = None

        # Parameters
        self.parameters = {
            'number_size': 16,
            'line_width': 2,
            'detail_level': 5,
            'min_region_size': 20,
            'simplify_epsilon': 1.0,
            'smoothing_iterations': 2,
            'corner_angle_threshold': 120,
            'show_outlines': False  # Default: outlines hidden (black is always visible)
        }

    def set_image_processor(self, processor: ImageProcessor):
        """Set image processor"""
        self.image_processor = processor

    def set_color_manager(self, manager: ColorManager):
        """Set color manager"""
        self.color_manager = manager

    def set_mode(self, mode: str):
        """Set visualization mode"""
        if mode in ['original', 'paintByNumbers', 'lineDrawing']:
            self.mode = mode
            logger.info(f"Set mode to: {mode}")
        else:
            logger.warning(f"Unknown mode: {mode}")

    def set_parameters(self, **kwargs):
        """Update parameters"""
        self.parameters.update(kwargs)

    def set_show_numbers(self, show: bool):
        """Toggle number visibility"""
        self.show_numbers = show

    def render(self, progress_callback=None) -> Optional[np.ndarray]:
        """
        Render current mode to numpy array

        Args:
            progress_callback: Optional callback(percent, message)

        Returns:
            RGB image as numpy array
        """
        if self.image_processor is None or self.image_processor.original_image is None:
            logger.error("No image loaded")
            return None

        if progress_callback:
            progress_callback(0, f"Rendering {self.mode}...")

        if self.mode == 'original':
            return self.render_original()

        elif self.mode == 'paintByNumbers':
            return self.render_paint_by_numbers(progress_callback)

        elif self.mode == 'lineDrawing':
            return self.render_line_drawing(progress_callback)

        return None

    def render_original(self) -> np.ndarray:
        """Render original image"""
        return self.image_processor.get_image_copy()

    def render_paint_by_numbers(self, progress_callback=None) -> Optional[np.ndarray]:
        """
        Render paint-by-numbers visualization
        Shows quantized colors + contours + numbers

        Args:
            progress_callback: Optional callback(percent, message)

        Returns:
            RGB image
        """
        if self.color_manager is None or self.color_manager.get_color_count() == 0:
            logger.warning("No colors available, rendering original")
            return self.render_original()

        if progress_callback:
            progress_callback(10, "Quantizing image...")

        # Quantize image if not cached
        if self.quantized_image is None or self.color_map is None:
            colors = self.color_manager.get_colors_as_array()
            self.quantized_image, self.color_map = self.image_processor.quantize_image(colors)

            if self.quantized_image is None:
                return None

        result = self.quantized_image.copy()

        if progress_callback:
            progress_callback(40, "Tracing contours...")

        # Draw contours (if enabled)
        if self.parameters.get('show_outlines'):
            result = self.draw_contours(result)

        # Fill black regions completely (ALWAYS, after contours so black stays on top)
        height, width = result.shape[:2]
        color_map_2d = self.color_map.reshape(height, width)
        for color in self.color_manager.get_colors():
            if hasattr(color, 'is_black') and color.is_black:
                # Fill all pixels of this color with pure black
                mask = color_map_2d == (color.number - 1)  # color numbers are 1-indexed
                result[mask] = [0, 0, 0]

        if progress_callback:
            progress_callback(70, "Placing numbers...")

        # Draw numbers
        if self.show_numbers:
            result = self.draw_numbers(result)

        if progress_callback:
            progress_callback(100, "Complete!")

        return result

    def render_line_drawing(self, progress_callback=None) -> Optional[np.ndarray]:
        """
        Render line drawing (contours only on white background)

        Args:
            progress_callback: Optional callback(percent, message)

        Returns:
            RGB image
        """
        if self.color_manager is None or self.color_manager.get_color_count() == 0:
            logger.warning("No colors available, using edge detection")
            return self.render_edge_detection(progress_callback)

        if progress_callback:
            progress_callback(10, "Quantizing image...")

        # Ensure we have quantized data
        if self.quantized_image is None or self.color_map is None:
            colors = self.color_manager.get_colors_as_array()
            self.quantized_image, self.color_map = self.image_processor.quantize_image(colors)

            if self.quantized_image is None:
                return None

        # Create white background
        height, width = self.quantized_image.shape[:2]
        result = np.ones((height, width, 3), dtype=np.uint8) * 255

        if progress_callback:
            progress_callback(40, "Tracing contours...")

        # Draw contours (if enabled)
        if self.parameters.get('show_outlines'):
            # For black regions, only draw external boundary (not internal details)
            result = self.draw_contours(result, exclude_internal_for_black=True)

        # Fill black regions completely (ALWAYS, after contours so black stays on top)
        color_map_2d = self.color_map.reshape(height, width)
        for color in self.color_manager.get_colors():
            if hasattr(color, 'is_black') and color.is_black:
                # Fill all pixels of this color with pure black
                mask = color_map_2d == (color.number - 1)  # color numbers are 1-indexed
                result[mask] = [0, 0, 0]
                logger.info(f"Filled black regions: {np.sum(mask)} pixels")

        if progress_callback:
            progress_callback(70, "Placing numbers...")

        # Draw numbers
        if self.show_numbers:
            result = self.draw_numbers(result)

        if progress_callback:
            progress_callback(100, "Complete!")

        return result

    def render_edge_detection(self, progress_callback=None) -> Optional[np.ndarray]:
        """Fallback: render using AI edge detection"""
        if progress_callback:
            progress_callback(0, "AI edge detection...")

        edges, corners = self.image_processor.detect_edges_advanced(
            use_multi_scale=True,
            preserve_corners=True,
            progress_callback=progress_callback
        )

        if edges is None:
            return self.render_original()

        # Convert edges to RGB
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

        # Invert (white background, black lines)
        edges_rgb = 255 - edges_rgb

        return edges_rgb

    def draw_contours(self, image: np.ndarray, exclude_internal_for_black: bool = False) -> np.ndarray:
        """
        Draw contours on image

        Args:
            image: RGB image
            exclude_internal_for_black: If True, skip internal contours within black regions

        Returns:
            Image with contours drawn
        """
        if self.color_map is None:
            return image

        height, width = image.shape[:2]

        # Trace contours if not cached
        if self.contours is None:
            self.contours = self.contour_tracer.trace_color_boundaries(
                self.color_map,
                width,
                height,
                simplify_epsilon=self.parameters['simplify_epsilon'],
                preserve_corners=True
            )

        # If excluding internal black contours, create a mask
        black_mask = None
        if exclude_internal_for_black and self.color_manager:
            black_mask = np.zeros((height, width), dtype=bool)
            color_map_2d = self.color_map.reshape(height, width)
            for color in self.color_manager.get_colors():
                if hasattr(color, 'is_black') and color.is_black:
                    mask = color_map_2d == (color.number - 1)
                    black_mask |= mask

            # Erode mask slightly so we keep the external boundary
            if np.any(black_mask):
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                black_mask = cv2.erode(black_mask.astype(np.uint8), kernel).astype(bool)

        # Draw contours
        result = image.copy()
        for contour in self.contours:
            # Skip if this contour is entirely within black region
            if black_mask is not None and len(contour) > 0:
                # Sample a few points from the contour
                sample_points = contour[::max(1, len(contour)//10)]
                points_in_black = 0
                for point in sample_points:
                    x, y = int(point[0][0]), int(point[0][1])
                    if 0 <= y < height and 0 <= x < width:
                        if black_mask[y, x]:
                            points_in_black += 1

                # If most points are in black, skip this contour
                if points_in_black > len(sample_points) * 0.8:
                    continue

            # Draw this contour
            cv2.drawContours(result, [contour], -1, (0, 0, 0), int(self.parameters['line_width']))

        return result

    def draw_numbers(self, image: np.ndarray) -> np.ndarray:
        """
        Draw numbers on image

        Args:
            image: RGB image

        Returns:
            Image with numbers drawn
        """
        if self.color_map is None or self.color_manager is None:
            return image

        height, width = image.shape[:2]
        color_map_2d = self.color_map.reshape(height, width)

        # Find regions if not cached
        if self.regions is None:
            self.regions = self.contour_tracer.find_region_centers(
                self.color_map,
                width,
                height,
                min_region_size=self.parameters['min_region_size']
            )

        # Draw numbers on each region
        result = image.copy()

        for region in self.regions:
            color_idx = region['color_idx']
            color = self.color_manager.get_color_by_index(color_idx)

            if color is None:
                continue

            # Skip numbers for white and black regions
            if hasattr(color, 'is_white') and color.is_white:
                continue  # Wit krijgt geen cijfers
            if hasattr(color, 'is_black') and color.is_black:
                continue  # Zwart krijgt geen cijfers

            # Get optimal center for this region
            center = self.contour_tracer.find_optimal_center(
                color_map_2d,
                width,
                height,
                region
            )

            # Calculate font size based on region size
            font_size = max(0.3, min(
                self.parameters['number_size'] / 20.0,
                np.sqrt(region['size']) / 50.0
            ))

            number_text = str(color.number)

            # Get text size for proper positioning
            # Use FONT_HERSHEY_DUPLEX for better quality than SIMPLEX
            font = cv2.FONT_HERSHEY_DUPLEX
            # Calculate thickness for sharper rendering
            text_thickness = max(1, int(font_size * 3))
            (text_width, text_height), _ = cv2.getTextSize(
                number_text,
                font,
                font_size,
                thickness=text_thickness
            )

            # Center text
            text_x = int(center[0] - text_width / 2)
            text_y = int(center[1] + text_height / 2)

            # Draw white outline for visibility (thinner for sharper look)
            outline_thickness = max(2, int(font_size * 4))
            cv2.putText(
                result,
                number_text,
                (text_x, text_y),
                font,
                font_size,
                (255, 255, 255),  # White outline
                thickness=outline_thickness,
                lineType=cv2.LINE_AA
            )

            # Draw black number on top
            cv2.putText(
                result,
                number_text,
                (text_x, text_y),
                font,
                font_size,
                (0, 0, 0),  # Black text
                thickness=text_thickness,
                lineType=cv2.LINE_AA
            )

        return result

    def render_current_mode(self, progress_callback=None) -> Optional[np.ndarray]:
        """
        Re-render current mode without recomputing quantization
        Used for toggling numbers in presentation mode

        Args:
            progress_callback: Optional callback(percent, message)

        Returns:
            RGB image
        """
        if self.mode == 'original':
            return self.render_original()

        elif self.mode == 'paintByNumbers' and self.quantized_image is not None:
            result = self.quantized_image.copy()

            # Draw contours if enabled
            if self.parameters.get('show_outlines'):
                result = self.draw_contours(result)

            # Fill black regions completely (ALWAYS, even if outlines are off)
            if self.color_map is not None and self.color_manager:
                height, width = result.shape[:2]
                color_map_2d = self.color_map.reshape(height, width)
                for color in self.color_manager.get_colors():
                    if hasattr(color, 'is_black') and color.is_black:
                        mask = color_map_2d == (color.number - 1)
                        result[mask] = [0, 0, 0]

            if self.show_numbers:
                result = self.draw_numbers(result)
            return result

        elif self.mode == 'lineDrawing' and self.quantized_image is not None:
            height, width = self.quantized_image.shape[:2]
            result = np.ones((height, width, 3), dtype=np.uint8) * 255

            # Draw contours if enabled (exclude internal black contours)
            if self.parameters.get('show_outlines'):
                result = self.draw_contours(result, exclude_internal_for_black=True)

            # Fill black regions completely (ALWAYS, after contours so black stays on top)
            if self.color_map is not None and self.color_manager:
                color_map_2d = self.color_map.reshape(height, width)
                for color in self.color_manager.get_colors():
                    if hasattr(color, 'is_black') and color.is_black:
                        mask = color_map_2d == (color.number - 1)
                        result[mask] = [0, 0, 0]

            if self.show_numbers:
                result = self.draw_numbers(result)
            return result

        else:
            # Fallback: full render
            return self.render(progress_callback)

    def clear_cache(self):
        """Clear cached rendering data"""
        self.quantized_image = None
        self.color_map = None
        self.contours = None
        self.regions = None
        logger.info("Cleared rendering cache")

    def export_svg(self) -> Optional[str]:
        """
        Export current visualization as SVG
        TODO: Implement SVG export

        Returns:
            SVG string
        """
        logger.warning("SVG export not yet implemented")
        return None

    def get_region_stats(self) -> Optional[Dict]:
        """
        Get statistics for color regions

        Returns:
            Dictionary with region statistics
        """
        if self.color_map is None or self.color_manager is None:
            return None

        return self.image_processor.calculate_region_stats(
            self.color_map,
            self.color_manager.get_colors_as_array()
        )
