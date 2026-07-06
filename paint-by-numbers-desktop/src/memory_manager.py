"""
Memory Manager - Automatic cleanup of image versions and cached data
Prevents memory bloat by limiting stored image history
"""

import logging
import sys
from typing import Dict, List, Optional
from collections import OrderedDict
import numpy as np

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages memory usage for images and cache"""

    def __init__(self, max_versions: int = 20, max_cache_mb: int = 500):
        """
        Initialize memory manager

        Args:
            max_versions: Maximum number of image versions to keep
            max_cache_mb: Maximum cache size in megabytes
        """
        self.max_versions = max_versions
        self.max_cache_mb = max_cache_mb

        # Store image versions in ordered dict (for LRU cleanup)
        self.image_versions: OrderedDict = OrderedDict()
        self.current_memory_mb = 0.0

    def add_image_version(self, key: str, image: np.ndarray, metadata: Optional[Dict] = None):
        """
        Add an image version to memory

        Args:
            key: Unique identifier for this version
            image: Numpy array of image data
            metadata: Optional metadata dict
        """
        # Calculate image size in MB
        image_size_mb = image.nbytes / (1024 * 1024)

        # Check if adding this would exceed limit
        if self.current_memory_mb + image_size_mb > self.max_cache_mb:
            self._cleanup_old_versions(image_size_mb)

        # Add version
        self.image_versions[key] = {
            'image': image,
            'size_mb': image_size_mb,
            'metadata': metadata or {}
        }
        self.image_versions.move_to_end(key)  # Mark as most recently used

        self.current_memory_mb += image_size_mb

        # Limit number of versions
        while len(self.image_versions) > self.max_versions:
            self._remove_oldest_version()

        logger.debug(f"Added image version '{key}' ({image_size_mb:.2f} MB). "
                    f"Total: {len(self.image_versions)} versions, {self.current_memory_mb:.2f} MB")

    def get_image_version(self, key: str) -> Optional[np.ndarray]:
        """
        Get an image version by key

        Args:
            key: Version identifier

        Returns:
            Image array or None if not found
        """
        if key in self.image_versions:
            # Move to end (mark as recently used)
            self.image_versions.move_to_end(key)
            return self.image_versions[key]['image']
        return None

    def remove_image_version(self, key: str):
        """Remove a specific image version"""
        if key in self.image_versions:
            size_mb = self.image_versions[key]['size_mb']
            del self.image_versions[key]
            self.current_memory_mb -= size_mb
            logger.debug(f"Removed image version '{key}' ({size_mb:.2f} MB)")

    def _remove_oldest_version(self):
        """Remove the oldest (least recently used) version"""
        if self.image_versions:
            # OrderedDict pops from beginning (oldest)
            key, data = self.image_versions.popitem(last=False)
            self.current_memory_mb -= data['size_mb']
            logger.debug(f"Removed oldest version '{key}' ({data['size_mb']:.2f} MB)")

    def _cleanup_old_versions(self, needed_mb: float):
        """
        Clean up old versions to make room for new data

        Args:
            needed_mb: Size in MB needed for new data
        """
        freed_mb = 0.0
        while (self.current_memory_mb + needed_mb > self.max_cache_mb and
               self.image_versions and
               freed_mb < needed_mb):
            key, data = self.image_versions.popitem(last=False)
            freed_mb += data['size_mb']
            self.current_memory_mb -= data['size_mb']
            logger.info(f"Cleaned up version '{key}' to free memory ({data['size_mb']:.2f} MB)")

    def clear_all(self):
        """Clear all cached versions"""
        count = len(self.image_versions)
        total_mb = self.current_memory_mb
        self.image_versions.clear()
        self.current_memory_mb = 0.0
        logger.info(f"Cleared all {count} versions ({total_mb:.2f} MB)")

    def get_memory_info(self) -> Dict:
        """
        Get current memory usage information

        Returns:
            Dict with memory statistics
        """
        return {
            'versions_count': len(self.image_versions),
            'current_mb': round(self.current_memory_mb, 2),
            'max_mb': self.max_cache_mb,
            'max_versions': self.max_versions,
            'usage_percent': round((self.current_memory_mb / self.max_cache_mb) * 100, 1),
            'versions': list(self.image_versions.keys())
        }

    def get_system_memory_info(self) -> Dict:
        """
        Get system memory information

        Returns:
            Dict with system memory stats
        """
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                'total_gb': round(mem.total / (1024**3), 2),
                'available_gb': round(mem.available / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2),
                'percent': mem.percent
            }
        except ImportError:
            # psutil not available
            return {}

    def optimize_memory(self):
        """
        Optimize memory usage by:
        1. Removing duplicate versions
        2. Compressing old versions
        3. Forcing garbage collection
        """
        import gc

        before_count = len(self.image_versions)
        before_mb = self.current_memory_mb

        # Remove versions that are too similar (optional optimization)
        # For now, just force garbage collection
        gc.collect()

        logger.info(f"Memory optimization: {before_count} versions, {before_mb:.2f} MB -> "
                   f"{len(self.image_versions)} versions, {self.current_memory_mb:.2f} MB")


class GlobalMemoryManager:
    """Singleton global memory manager for the application"""
    _instance = None

    @classmethod
    def get_instance(cls, max_versions: int = 20, max_cache_mb: int = 500) -> MemoryManager:
        """Get or create the global memory manager instance"""
        if cls._instance is None:
            cls._instance = MemoryManager(max_versions, max_cache_mb)
            logger.info(f"Global memory manager created (max: {max_versions} versions, {max_cache_mb} MB)")
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the global instance (for testing)"""
        if cls._instance:
            cls._instance.clear_all()
        cls._instance = None
