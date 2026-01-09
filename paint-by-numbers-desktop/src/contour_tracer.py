"""
Contour Tracer - Advanced contour detection with OpenCV
Converts JavaScript contourTracer.js to high-performance Python
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ContourTracer:
    """High-performance contour tracing with OpenCV"""

    def __init__(self):
        self.simplify_epsilon = 1.0
        self.smoothing_iterations = 2
        self.corner_angle_threshold = 120  # degrees

    def trace_color_boundaries(
        self,
        color_map: np.ndarray,
        width: int,
        height: int,
        simplify_epsilon: float = 1.0,
        preserve_corners: bool = True
    ) -> List[np.ndarray]:
        """
        Trace boundaries between color regions
        Much faster than JavaScript Marching Squares implementation

        Args:
            color_map: 1D array mapping pixels to color indices
            width: Image width
            height: Image height
            simplify_epsilon: RDP simplification tolerance
            preserve_corners: Keep sharp corners

        Returns:
            List of contour arrays, each shape (n_points, 1, 2)
        """
        logger.info("Tracing color boundaries with OpenCV...")

        # Reshape color map to 2D
        color_map_2d = color_map.reshape(height, width).astype(np.uint8)

        all_contours = []

        # Find unique colors
        unique_colors = np.unique(color_map_2d)

        for color_idx in unique_colors:
            # Create binary mask for this color
            mask = (color_map_2d == color_idx).astype(np.uint8) * 255

            # Find contours for this color region
            # RETR_LIST gets all contours (no hierarchy)
            # CHAIN_APPROX_SIMPLE compresses horizontal/vertical segments
            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_LIST,
                cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                # Skip very small contours
                if len(contour) < 3:
                    continue

                # Simplify contour with Ramer-Douglas-Peucker
                epsilon = simplify_epsilon
                simplified = cv2.approxPolyDP(contour, epsilon, closed=True)

                # Optional: preserve corners
                if preserve_corners:
                    simplified = self._preserve_sharp_corners(
                        simplified,
                        self.corner_angle_threshold
                    )

                all_contours.append(simplified)

        logger.info(f"Found {len(all_contours)} contours")
        return all_contours

    def _preserve_sharp_corners(
        self,
        contour: np.ndarray,
        angle_threshold: float = 120
    ) -> np.ndarray:
        """
        Preserve sharp corners in contour
        Angles sharper than threshold are kept without smoothing

        Args:
            contour: Contour array of shape (n, 1, 2)
            angle_threshold: Threshold in degrees

        Returns:
            Contour with preserved corners
        """
        if len(contour) < 3:
            return contour

        # Detect corners based on angle
        corners = []
        points = contour[:, 0, :]  # Remove middle dimension

        for i in range(len(points)):
            p1 = points[(i - 1) % len(points)]
            p2 = points[i]
            p3 = points[(i + 1) % len(points)]

            # Calculate angle between vectors
            v1 = p1 - p2
            v2 = p3 - p2

            # Normalize vectors
            v1_norm = np.linalg.norm(v1)
            v2_norm = np.linalg.norm(v2)

            if v1_norm < 1e-6 or v2_norm < 1e-6:
                continue

            v1 = v1 / v1_norm
            v2 = v2 / v2_norm

            # Calculate angle using dot product
            cos_angle = np.clip(np.dot(v1, v2), -1.0, 1.0)
            angle = np.degrees(np.arccos(cos_angle))

            # If angle is sharp (< threshold), mark as corner
            if angle < angle_threshold:
                corners.append(i)

        # Mark corners in contour metadata (for later smoothing)
        # For now, just return original contour
        # More sophisticated smoothing could skip corners
        return contour

    def smooth_contour_chaikin(
        self,
        contour: np.ndarray,
        iterations: int = 2,
        preserve_corners: bool = True,
        corner_indices: Optional[List[int]] = None
    ) -> np.ndarray:
        """
        Smooth contour using Chaikin's corner cutting algorithm
        Optionally preserves sharp corners

        Args:
            contour: Contour array of shape (n, 1, 2)
            iterations: Number of smoothing iterations
            preserve_corners: Whether to preserve corners
            corner_indices: List of corner point indices to preserve

        Returns:
            Smoothed contour
        """
        if len(contour) < 3 or iterations == 0:
            return contour

        points = contour[:, 0, :].copy()  # Remove middle dimension

        for _ in range(iterations):
            new_points = []

            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]

                # Check if either point is a corner
                is_corner = False
                if preserve_corners and corner_indices is not None:
                    is_corner = i in corner_indices or (i + 1) % len(points) in corner_indices

                if is_corner:
                    # Don't smooth corners
                    new_points.append(p1)
                else:
                    # Chaikin's algorithm: split edge into two points
                    q = 0.75 * p1 + 0.25 * p2
                    r = 0.25 * p1 + 0.75 * p2
                    new_points.append(q)
                    new_points.append(r)

            points = np.array(new_points)

        # Reshape back to OpenCV contour format
        return points.reshape(-1, 1, 2).astype(np.int32)

    def draw_contours_on_image(
        self,
        image: np.ndarray,
        contours: List[np.ndarray],
        color: Tuple[int, int, int] = (0, 0, 0),
        thickness: int = 2
    ) -> np.ndarray:
        """
        Draw contours on image

        Args:
            image: RGB image
            contours: List of contours
            color: Line color (R, G, B)
            thickness: Line thickness

        Returns:
            Image with drawn contours
        """
        result = image.copy()

        # Draw all contours
        cv2.drawContours(
            result,
            contours,
            -1,  # Draw all contours
            color,
            thickness,
            lineType=cv2.LINE_AA  # Anti-aliased lines
        )

        return result

    def contour_to_path(self, contour: np.ndarray) -> List[Tuple[int, int]]:
        """
        Convert OpenCV contour to list of (x, y) points

        Args:
            contour: OpenCV contour array

        Returns:
            List of (x, y) tuples
        """
        points = contour[:, 0, :]
        return [(int(p[0]), int(p[1])) for p in points]

    def find_region_centers(
        self,
        color_map: np.ndarray,
        width: int,
        height: int,
        min_region_size: int = 20
    ) -> List[dict]:
        """
        Find center points of color regions for number placement
        Uses connected components analysis

        Args:
            color_map: 1D array mapping pixels to color indices
            width: Image width
            height: Image height
            min_region_size: Minimum region size to include

        Returns:
            List of region info dicts with 'color_idx', 'center', 'size'
        """
        color_map_2d = color_map.reshape(height, width).astype(np.uint8)
        unique_colors = np.unique(color_map_2d)

        regions = []

        for color_idx in unique_colors:
            # Create binary mask
            mask = (color_map_2d == color_idx).astype(np.uint8) * 255

            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                mask,
                connectivity=8
            )

            # Skip background (label 0)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]

                if area >= min_region_size:
                    cx, cy = centroids[i]

                    regions.append({
                        'color_idx': int(color_idx),
                        'center': (int(cx), int(cy)),
                        'size': int(area),
                        'bbox': {
                            'x': int(stats[i, cv2.CC_STAT_LEFT]),
                            'y': int(stats[i, cv2.CC_STAT_TOP]),
                            'width': int(stats[i, cv2.CC_STAT_WIDTH]),
                            'height': int(stats[i, cv2.CC_STAT_HEIGHT])
                        }
                    })

        logger.info(f"Found {len(regions)} regions")
        return regions

    def find_optimal_center(
        self,
        color_map: np.ndarray,
        width: int,
        height: int,
        region_info: dict
    ) -> Tuple[int, int]:
        """
        Find optimal center point for number placement
        Uses distance transform to find point furthest from edges

        Args:
            color_map: 2D color map array
            width: Image width
            height: Image height
            region_info: Region information dict

        Returns:
            (x, y) tuple of optimal center point
        """
        color_idx = region_info['color_idx']
        bbox = region_info['bbox']

        # Extract region bounding box
        x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']

        # Expand bbox slightly
        padding = 5
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(width, x + w + padding)
        y2 = min(height, y + h + padding)

        # Extract region
        region = color_map[y1:y2, x1:x2]
        mask = (region == color_idx).astype(np.uint8) * 255

        # Distance transform
        dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

        # Find maximum distance point
        _, _, _, max_loc = cv2.minMaxLoc(dist_transform)

        # Convert back to full image coordinates
        optimal_x = x1 + max_loc[0]
        optimal_y = y1 + max_loc[1]

        return (optimal_x, optimal_y)
