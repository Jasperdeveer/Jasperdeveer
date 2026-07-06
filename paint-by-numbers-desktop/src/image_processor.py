"""
Image Processor - Core image processing with OpenCV
Converts JavaScript imageProcessor.js to Python with performance optimizations
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict
from sklearn.cluster import KMeans
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageProcessor:
    """High-performance image processing with OpenCV"""

    def __init__(self):
        self.original_image = None
        self.width = 0
        self.height = 0

    def load_image(self, file_path: str) -> bool:
        """
        Load image from file path
        Automatically scales down large images to max 4500px to improve performance

        Args:
            file_path: Path to image file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load image with OpenCV (BGR format)
            img = cv2.imread(file_path)

            if img is None:
                logger.error(f"Failed to load image: {file_path}")
                return False

            # Convert BGR to RGB for consistency
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width = img_rgb.shape[:2]

            # Scale down if image is too large (max 4500px on longest side)
            MAX_DIMENSION = 4500
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                # Calculate scaling factor to fit within MAX_DIMENSION
                scale = MAX_DIMENSION / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)

                logger.info(f"Scaling down image from {width}x{height} to {new_width}x{new_height} for performance")
                img_rgb = cv2.resize(img_rgb, (new_width, new_height), interpolation=cv2.INTER_AREA)

            self.original_image = img_rgb
            self.height, self.width = self.original_image.shape[:2]

            logger.info(f"Loaded image: {self.width}x{self.height}")
            return True

        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return False

    def load_image_from_array(self, img_array: np.ndarray) -> bool:
        """
        Load image from numpy array (for drag & drop)
        Automatically scales down large images to max 4500px to improve performance
        """
        try:
            if len(img_array.shape) == 2:
                # Grayscale -> RGB
                img_rgb = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
            elif img_array.shape[2] == 4:
                # RGBA -> RGB
                img_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
            else:
                img_rgb = img_array

            height, width = img_rgb.shape[:2]

            # Scale down if image is too large (max 4500px on longest side)
            MAX_DIMENSION = 4500
            if width > MAX_DIMENSION or height > MAX_DIMENSION:
                # Calculate scaling factor to fit within MAX_DIMENSION
                scale = MAX_DIMENSION / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)

                logger.info(f"Scaling down image from {width}x{height} to {new_width}x{new_height} for performance")
                img_rgb = cv2.resize(img_rgb, (new_width, new_height), interpolation=cv2.INTER_AREA)

            self.original_image = img_rgb
            self.height, self.width = self.original_image.shape[:2]
            return True
        except Exception as e:
            logger.error(f"Error loading image from array: {e}")
            return False

    def detect_colors(self, num_colors: int, max_iterations: int = 100) -> np.ndarray:
        """
        Detect dominant colors using K-means clustering
        Much faster than JavaScript version using sklearn

        Args:
            num_colors: Number of colors to detect
            max_iterations: Max K-means iterations

        Returns:
            numpy array of shape (num_colors, 3) with RGB colors
        """
        if self.original_image is None:
            logger.error("No image loaded")
            return np.array([])

        logger.info(f"Detecting {num_colors} colors using K-means clustering...")

        # Reshape image to 2D array of pixels
        pixels = self.original_image.reshape(-1, 3).astype(np.float32)

        # Downsample for speed if image is very large
        if len(pixels) > 100000:
            # Sample 100k random pixels
            indices = np.random.choice(len(pixels), 100000, replace=False)
            pixels = pixels[indices]

        # K-means clustering (much faster than JS implementation)
        kmeans = KMeans(
            n_clusters=num_colors,
            max_iter=max_iterations,
            n_init=10,
            random_state=42
        )
        kmeans.fit(pixels)

        # Get cluster centers (dominant colors)
        colors = kmeans.cluster_centers_.astype(np.uint8)

        logger.info(f"Detected colors: {colors}")
        return colors

    def quantize_image(self, colors: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Quantize image to given color palette
        Returns quantized image and color map (pixel -> color index)

        Args:
            colors: Array of shape (n_colors, 3) with RGB colors

        Returns:
            Tuple of (quantized_image, color_map)
            - quantized_image: RGB image with only palette colors
            - color_map: 1D array mapping each pixel to color index
        """
        if self.original_image is None:
            logger.error("No image loaded")
            return None, None

        logger.info("Quantizing image to color palette...")

        # Reshape image to 2D array of pixels
        pixels = self.original_image.reshape(-1, 3).astype(np.float32)

        # Convert colors to float32
        palette = colors.astype(np.float32)

        # Find nearest color for each pixel using vectorized operations
        # Calculate distances to all colors at once (memory efficient)
        color_map = np.zeros(len(pixels), dtype=np.uint8)

        # Process in batches to avoid memory issues
        batch_size = 10000
        for i in range(0, len(pixels), batch_size):
            batch = pixels[i:i+batch_size]

            # Calculate Euclidean distance to all colors
            distances = np.sqrt(((batch[:, np.newaxis] - palette) ** 2).sum(axis=2))

            # Find nearest color index
            color_map[i:i+batch_size] = np.argmin(distances, axis=1)

        # Create quantized image
        quantized_pixels = colors[color_map]
        quantized_image = quantized_pixels.reshape(self.height, self.width, 3)

        logger.info("Quantization complete")
        return quantized_image, color_map

    def detect_edges_advanced(
        self,
        use_multi_scale: bool = True,
        preserve_corners: bool = True,
        progress_callback=None
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Advanced AI-powered edge detection
        Converts aiEdgeDetector.js to OpenCV implementation

        Args:
            use_multi_scale: Use multi-scale detection
            preserve_corners: Preserve sharp corners
            progress_callback: Optional callback(percent, message)

        Returns:
            Tuple of (edges, corners)
        """
        if self.original_image is None:
            return None, None

        if progress_callback:
            progress_callback(0, "Converting to grayscale...")

        # Convert to grayscale
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2GRAY)

        # Bilateral filtering (noise reduction while preserving edges)
        if progress_callback:
            progress_callback(10, "Applying bilateral filter...")

        filtered = cv2.bilateralFilter(gray, 9, 75, 75)

        corners = None
        if preserve_corners:
            if progress_callback:
                progress_callback(20, "Detecting corners with Harris...")

            # Harris corner detection
            corners = cv2.cornerHarris(
                filtered.astype(np.float32),
                blockSize=2,
                ksize=3,
                k=0.04
            )
            corners = cv2.dilate(corners, None)

        if use_multi_scale:
            if progress_callback:
                progress_callback(30, "Multi-scale edge detection...")

            # Multi-scale edge detection
            edges_fine = cv2.Canny(filtered, 50, 150)
            edges_medium = cv2.Canny(
                cv2.GaussianBlur(filtered, (5, 5), 1.5),
                30, 100
            )
            edges_coarse = cv2.Canny(
                cv2.GaussianBlur(filtered, (9, 9), 3.0),
                20, 80
            )

            # Weighted combination
            edges = cv2.addWeighted(
                cv2.addWeighted(edges_fine, 0.3, edges_medium, 0.4, 0),
                1.0,
                edges_coarse,
                0.3,
                0
            )
        else:
            if progress_callback:
                progress_callback(40, "Canny edge detection...")

            # Standard Canny edge detection
            edges = cv2.Canny(filtered, 50, 150)

        if progress_callback:
            progress_callback(60, "Morphological operations...")

        # Morphological operations to clean up edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        if progress_callback:
            progress_callback(80, "Thinning edges...")

        # Thinning for cleaner lines
        edges = self._zhang_suen_thinning(edges)

        if progress_callback:
            progress_callback(100, "Complete!")

        return edges, corners

    def _zhang_suen_thinning(self, img: np.ndarray) -> np.ndarray:
        """Zhang-Suen thinning algorithm for single-pixel width edges"""
        # OpenCV has a built-in thinning function
        thinned = cv2.ximgproc.thinning(img, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
        return thinned

    def calculate_region_stats(
        self,
        color_map: np.ndarray,
        colors: np.ndarray
    ) -> Dict[int, Dict]:
        """
        Calculate statistics for each color region

        Args:
            color_map: 1D array mapping pixels to color indices
            colors: Array of RGB colors

        Returns:
            Dictionary with region stats per color
        """
        stats = {}

        for color_idx in range(len(colors)):
            # Count pixels of this color
            pixel_count = np.sum(color_map == color_idx)

            if pixel_count == 0:
                continue

            stats[color_idx] = {
                'pixel_count': int(pixel_count),
                'percentage': float(pixel_count / len(color_map) * 100),
                'color': colors[color_idx].tolist()
            }

        return stats

    def resize_image(self, max_width: int, max_height: int) -> bool:
        """Resize image to fit within max dimensions while preserving aspect ratio"""
        if self.original_image is None:
            return False

        h, w = self.original_image.shape[:2]

        # Calculate scaling factor
        scale = min(max_width / w, max_height / h)

        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)

            self.original_image = cv2.resize(
                self.original_image,
                (new_w, new_h),
                interpolation=cv2.INTER_AREA
            )
            self.width = new_w
            self.height = new_h

            logger.info(f"Resized image to {new_w}x{new_h}")

        return True

    def get_image_copy(self) -> Optional[np.ndarray]:
        """Get a copy of the original image"""
        if self.original_image is None:
            return None
        return self.original_image.copy()
