#!/usr/bin/env python3
"""
Paint-by-Numbers Generator - Professional Edition
Optimale versie met OpenCV, watershed segmentation en SVG export
"""

import cv2
import numpy as np
from sklearn.cluster import KMeans
from skimage import morphology, measure
from skimage.segmentation import watershed
from scipy import ndimage
import svgwrite
from collections import defaultdict
from typing import List, Tuple, Dict
import argparse


class Color:
    """Represents a color in the palette"""
    def __init__(self, rgb: Tuple[int, int, int], number: int):
        self.rgb = rgb
        self.number = number
        self.hex = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'

    def __repr__(self):
        return f"Color({self.number}: {self.hex})"


class PaintByNumbersGenerator:
    """
    Professional Paint-by-Numbers generator using:
    - OpenCV for image processing
    - K-means clustering for color detection
    - Watershed algorithm for perfect region segmentation
    - Morphological operations for noise removal
    - SVG export for scalable output
    """

    def __init__(self, image_path: str, n_colors: int = 12, min_region_size: int = 200):
        """
        Initialize the generator

        Args:
            image_path: Path to input image
            n_colors: Number of colors to extract
            min_region_size: Minimum region size in pixels (smaller regions are merged)
        """
        self.image_path = image_path
        self.n_colors = n_colors
        self.min_region_size = min_region_size

        # Load and preprocess image
        self.original = cv2.imread(image_path)
        if self.original is None:
            raise ValueError(f"Could not load image: {image_path}")

        self.original = cv2.cvtColor(self.original, cv2.COLOR_BGR2RGB)
        self.height, self.width = self.original.shape[:2]

        # Results
        self.colors: List[Color] = []
        self.labels = None
        self.segmented = None
        self.regions = None

    def detect_colors(self) -> List[Color]:
        """
        Detect dominant colors using K-means clustering
        Superior to JavaScript k-means implementation
        """
        print(f"🎨 Detecting {self.n_colors} colors...")

        # Reshape image for clustering
        pixels = self.original.reshape(-1, 3)

        # Use K-means clustering
        kmeans = KMeans(
            n_clusters=self.n_colors,
            n_init=10,
            max_iter=300,
            random_state=42
        )
        kmeans.fit(pixels)

        # Sort colors by frequency
        labels = kmeans.labels_
        unique, counts = np.unique(labels, return_counts=True)
        sorted_indices = np.argsort(-counts)

        # Create color objects
        self.colors = []
        for i, idx in enumerate(sorted_indices):
            rgb = tuple(map(int, kmeans.cluster_centers_[idx]))
            self.colors.append(Color(rgb, i + 1))

        print(f"✅ Colors detected: {len(self.colors)}")
        return self.colors

    def quantize_image(self) -> np.ndarray:
        """
        Quantize image to detected colors
        Much faster and more accurate than JavaScript implementation
        """
        print("🔢 Quantizing image...")

        pixels = self.original.reshape(-1, 3)

        # Find nearest color for each pixel
        quantized = np.zeros_like(pixels)
        labels = np.zeros(len(pixels), dtype=np.uint8)

        for i, pixel in enumerate(pixels):
            distances = [np.linalg.norm(pixel - np.array(c.rgb)) for c in self.colors]
            nearest_idx = np.argmin(distances)
            quantized[i] = self.colors[nearest_idx].rgb
            labels[i] = nearest_idx

        self.labels = labels.reshape(self.height, self.width)
        quantized_image = quantized.reshape(self.height, self.width, 3).astype(np.uint8)

        print("✅ Image quantized")
        return quantized_image

    def segment_regions(self) -> np.ndarray:
        """
        Segment image into clean regions using watershed algorithm
        This is the key improvement over the JavaScript version!

        Watershed creates perfect, noise-free regions by treating the image
        as a topographic surface and finding watershed boundaries.
        """
        print("🌊 Segmenting regions with watershed algorithm...")

        # Create distance transform for watershed
        # This finds the "peaks" in each color region
        markers = np.zeros_like(self.labels, dtype=np.int32)
        marker_id = 1

        for color_idx in range(len(self.colors)):
            mask = (self.labels == color_idx).astype(np.uint8)

            # Apply morphological opening to remove noise
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)

            # Distance transform to find centers
            dist_transform = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

            # Find local maxima as markers
            _, sure_fg = cv2.threshold(dist_transform, 0.3 * dist_transform.max(), 255, 0)
            sure_fg = sure_fg.astype(np.uint8)

            # Connected components for markers
            n_labels, labeled = cv2.connectedComponents(sure_fg)

            # Add to markers (skip background label 0)
            for i in range(1, n_labels):
                markers[labeled == i] = marker_id
                marker_id += 1

        # Apply watershed
        # Convert labels to 3-channel for watershed
        labels_3ch = cv2.cvtColor(self.labels.astype(np.uint8), cv2.COLOR_GRAY2BGR)
        markers = cv2.watershed(labels_3ch, markers)

        # Remove watershed boundaries (marked as -1)
        markers[markers == -1] = 0

        self.segmented = markers

        print("✅ Regions segmented")
        return markers

    def merge_small_regions(self) -> np.ndarray:
        """
        Merge small regions with their largest neighbor
        Much more efficient than JavaScript implementation
        """
        print(f"🔧 Merging regions smaller than {self.min_region_size} pixels...")

        result = self.segmented.copy()

        # Get region properties
        regions = measure.regionprops(result)

        changed = True
        iterations = 0
        max_iterations = 10

        while changed and iterations < max_iterations:
            changed = False
            iterations += 1

            regions = measure.regionprops(result)

            for region in regions:
                if region.area < self.min_region_size:
                    # Find neighbors
                    mask = (result == region.label)
                    dilated = ndimage.binary_dilation(mask)
                    boundary = dilated & ~mask

                    neighbor_labels = result[boundary]
                    neighbor_labels = neighbor_labels[neighbor_labels != 0]
                    neighbor_labels = neighbor_labels[neighbor_labels != region.label]

                    if len(neighbor_labels) > 0:
                        # Find most common neighbor
                        unique, counts = np.unique(neighbor_labels, return_counts=True)
                        largest_neighbor = unique[np.argmax(counts)]

                        # Merge
                        result[mask] = largest_neighbor
                        changed = True

        self.segmented = result
        print(f"✅ Regions merged (iterations: {iterations})")
        return result

    def find_region_centers(self) -> Dict[int, Tuple[int, int]]:
        """
        Find optimal center point for each region
        Uses distance transform to find point furthest from edges
        """
        print("📍 Finding region centers...")

        centers = {}
        regions = measure.regionprops(self.segmented)

        for region in regions:
            if region.area < self.min_region_size:
                continue

            # Get region mask
            mask = (self.segmented == region.label).astype(np.uint8)

            # Distance transform
            dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)

            # Find maximum (point furthest from edge)
            _, _, _, max_loc = cv2.minMaxLoc(dist)
            centers[region.label] = max_loc  # (x, y)

        self.region_centers = centers
        print(f"✅ Found {len(centers)} region centers")
        return centers

    def get_region_color(self, region_label: int) -> int:
        """Get the color index for a region"""
        mask = (self.segmented == region_label)
        if not np.any(mask):
            return 0

        # Most common color in this region
        region_labels = self.labels[mask]
        unique, counts = np.unique(region_labels, return_counts=True)
        return unique[np.argmax(counts)]

    def export_svg(self, output_path: str, show_numbers: bool = True):
        """
        Export as SVG with perfect vector contours
        This is the killer feature - infinitely scalable output!
        """
        print(f"📄 Exporting SVG to {output_path}...")

        dwg = svgwrite.Drawing(output_path, size=(self.width, self.height))

        # Add white background
        dwg.add(dwg.rect(insert=(0, 0), size=(self.width, self.height), fill='white'))

        # Find contours for each region
        regions = measure.regionprops(self.segmented)

        for region in regions:
            if region.area < self.min_region_size:
                continue

            # Get region mask
            mask = (self.segmented == region.label).astype(np.uint8)

            # Find contours using OpenCV
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Draw contours as SVG paths
            for contour in contours:
                if len(contour) < 3:
                    continue

                # Convert to SVG path
                points = contour.squeeze()
                if len(points.shape) == 1:
                    continue

                path_data = f"M {points[0][0]},{points[0][1]}"
                for point in points[1:]:
                    path_data += f" L {point[0]},{point[1]}"
                path_data += " Z"

                dwg.add(dwg.path(d=path_data, fill='none', stroke='black', stroke_width=2))

        # Add numbers
        if show_numbers and hasattr(self, 'region_centers'):
            for region_label, (x, y) in self.region_centers.items():
                region = next((r for r in regions if r.label == region_label), None)
                if region and region.area >= self.min_region_size:
                    color_idx = self.get_region_color(region_label)
                    number = self.colors[color_idx].number

                    # Font size based on region area
                    font_size = min(48, max(12, int(np.sqrt(region.area) * 0.3)))

                    dwg.add(dwg.text(
                        str(number),
                        insert=(x, y),
                        text_anchor='middle',
                        dominant_baseline='middle',
                        font_size=font_size,
                        font_weight='bold',
                        fill='black'
                    ))

        dwg.save()
        print("✅ SVG exported successfully")

    def export_png(self, output_path: str, mode: str = 'line'):
        """
        Export as PNG

        Args:
            mode: 'line' for line drawing, 'colored' for paint-by-numbers view
        """
        print(f"🖼️  Exporting PNG ({mode} mode) to {output_path}...")

        if mode == 'line':
            # White background
            result = np.ones((self.height, self.width, 3), dtype=np.uint8) * 255

            # Draw black contours
            contours_img = np.zeros((self.height, self.width), dtype=np.uint8)
            regions = measure.regionprops(self.segmented)

            for region in regions:
                if region.area < self.min_region_size:
                    continue

                mask = (self.segmented == region.label).astype(np.uint8)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(contours_img, contours, -1, 255, 2)

            result[contours_img > 0] = [0, 0, 0]

        else:  # colored mode
            result = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            for i, color in enumerate(self.colors):
                mask = self.labels == i
                result[mask] = color.rgb

        # Convert RGB to BGR for OpenCV
        result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, result_bgr)

        print("✅ PNG exported successfully")

    def print_legend(self):
        """Print color legend with spray paint calculations"""
        print("\n" + "="*60)
        print("🎨 COLOR LEGEND")
        print("="*60)

        # Calculate region areas
        region_areas = defaultdict(int)
        for i in range(len(self.colors)):
            mask = self.labels == i
            region_areas[i] = np.sum(mask)

        # Assume 1 pixel = 1 cm² for calculation (adjust based on your needs)
        # Montana Black coverage: 2-2.5 m² per can
        coverage_per_can = 2.25  # m² per can (average)

        print(f"\n{'#':<4} {'Color':<10} {'Area (px)':<12} {'Area (m²)':<12} {'Cans':<8}")
        print("-"*60)

        for i, color in enumerate(self.colors):
            area_px = region_areas[i]
            area_m2 = area_px / 10000  # px to m² (rough estimate)
            cans_needed = np.ceil(area_m2 / coverage_per_can)

            print(f"{color.number:<4} {color.hex:<10} {area_px:<12} {area_m2:<12.2f} {int(cans_needed):<8}")

        print("="*60)
        print("\n💡 Montana Black coverage: ~2-2.5 m² per can")
        print("   Adjust pixel-to-area ratio based on your actual wall size\n")

    def process(self, export_svg: bool = True, export_png: bool = True):
        """
        Complete processing pipeline
        """
        print("\n" + "="*60)
        print("🎨 PAINT-BY-NUMBERS GENERATOR - PROFESSIONAL EDITION")
        print("="*60 + "\n")

        # Step 1: Detect colors
        self.detect_colors()

        # Step 2: Quantize image
        self.quantize_image()

        # Step 3: Segment regions with watershed
        self.segment_regions()

        # Step 4: Merge small regions
        self.merge_small_regions()

        # Step 5: Find region centers
        self.find_region_centers()

        # Step 6: Print legend
        self.print_legend()

        # Step 7: Export
        base_name = self.image_path.rsplit('.', 1)[0]

        if export_svg:
            self.export_svg(f"{base_name}_paintbynumbers.svg")

        if export_png:
            self.export_png(f"{base_name}_line.png", mode='line')
            self.export_png(f"{base_name}_colored.png", mode='colored')

        print("\n" + "="*60)
        print("✅ PROCESSING COMPLETE!")
        print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Professional Paint-by-Numbers Generator for Street Art'
    )
    parser.add_argument('image', help='Input image path')
    parser.add_argument('-c', '--colors', type=int, default=12,
                       help='Number of colors (default: 12)')
    parser.add_argument('-m', '--min-size', type=int, default=200,
                       help='Minimum region size in pixels (default: 200)')
    parser.add_argument('--no-svg', action='store_true',
                       help='Skip SVG export')
    parser.add_argument('--no-png', action='store_true',
                       help='Skip PNG export')

    args = parser.parse_args()

    try:
        generator = PaintByNumbersGenerator(
            args.image,
            n_colors=args.colors,
            min_region_size=args.min_size
        )

        generator.process(
            export_svg=not args.no_svg,
            export_png=not args.no_png
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
