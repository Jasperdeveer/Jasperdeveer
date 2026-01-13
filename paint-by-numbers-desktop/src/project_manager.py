"""
Project Manager - Save and load JSPR projects
Handles serialization of entire project state
"""

import json
import base64
import numpy as np
import cv2
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from color_manager import Color, ColorManager

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages saving and loading of JSPR projects"""

    VERSION = "1.0"

    @staticmethod
    def save_project(
        file_path: str,
        image: np.ndarray,
        color_manager: ColorManager,
        parameters: Dict[str, Any],
        current_mode: str
    ) -> bool:
        """
        Save project to .jspr file

        Args:
            file_path: Path to save file
            image: Original image (RGB numpy array)
            color_manager: ColorManager instance
            parameters: Dict with line_width, number_size, min_region_size, show_outlines
            current_mode: Current visualization mode

        Returns:
            True if successful
        """
        try:
            # Ensure .jspr extension
            if not file_path.endswith('.jspr'):
                file_path += '.jspr'

            # Encode image as PNG in base64
            success, buffer = cv2.imencode('.png', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            if not success:
                logger.error("Failed to encode image")
                return False

            image_base64 = base64.b64encode(buffer).decode('utf-8')

            # Serialize colors
            colors_data = []
            for color in color_manager.get_colors():
                color_dict = {
                    'number': color.number,
                    'r': color.r,
                    'g': color.g,
                    'b': color.b,
                    'name': color.name,
                    'is_black': getattr(color, 'is_black', False),
                    'is_white': getattr(color, 'is_white', False)
                }
                colors_data.append(color_dict)

            # Build project data
            project_data = {
                'version': ProjectManager.VERSION,
                'image': image_base64,
                'image_shape': image.shape,
                'colors': colors_data,
                'parameters': parameters,
                'current_mode': current_mode
            }

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(project_data, f, indent=2)

            logger.info(f"Project saved to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save project: {e}", exc_info=True)
            return False

    @staticmethod
    def load_project(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Load project from .jspr file

        Args:
            file_path: Path to .jspr file

        Returns:
            Dict with 'image', 'colors', 'parameters', 'current_mode'
            None if failed
        """
        try:
            # Read file
            with open(file_path, 'r') as f:
                project_data = json.load(f)

            # Check version
            version = project_data.get('version', '1.0')
            if version != ProjectManager.VERSION:
                logger.warning(f"Project version mismatch: {version} vs {ProjectManager.VERSION}")

            # Decode image
            image_base64 = project_data['image']
            image_bytes = base64.b64decode(image_base64)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image_bgr = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

            # Deserialize colors
            colors = []
            for color_dict in project_data['colors']:
                color = Color(
                    r=color_dict['r'],
                    g=color_dict['g'],
                    b=color_dict['b'],
                    number=color_dict['number'],
                    name=color_dict['name'],
                    is_black=color_dict.get('is_black', False),
                    is_white=color_dict.get('is_white', False)
                )
                colors.append(color)

            # Return deserialized data
            result = {
                'image': image,
                'colors': colors,
                'parameters': project_data['parameters'],
                'current_mode': project_data['current_mode']
            }

            logger.info(f"Project loaded from: {file_path}")
            return result

        except Exception as e:
            logger.error(f"Failed to load project: {e}", exc_info=True)
            return None
