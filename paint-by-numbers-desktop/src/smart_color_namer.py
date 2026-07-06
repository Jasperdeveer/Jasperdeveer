"""
Smart Color Namer - AI/algorithm-based color name suggestions
Provides intelligent, descriptive names for colors based on:
- Distance to known color names database
- Color properties (hue, saturation, lightness)
- Context-aware naming (warm/cool, dark/light)
"""

import numpy as np
import logging
from typing import List, Tuple, Dict, Optional
import colorsys

logger = logging.getLogger(__name__)


# Comprehensive color names database (X11/CSS color names + descriptive names)
COLOR_NAMES_DB = {
    # Reds
    (255, 0, 0): "Rood",
    (220, 20, 60): "Karmijnrood",
    (139, 0, 0): "Donkerrood",
    (255, 99, 71): "Tomaatrood",
    (255, 69, 0): "Oranjerood",
    (178, 34, 34): "Vuursteenrood",
    (205, 92, 92): "Indisch rood",
    (240, 128, 128): "Lichtrood",

    # Oranges
    (255, 165, 0): "Oranje",
    (255, 140, 0): "Donkeroranje",
    (255, 127, 80): "Koraal",
    (255, 160, 122): "Lichtkoraal",
    (255, 218, 185): "Perzik",

    # Yellows
    (255, 255, 0): "Geel",
    (255, 255, 224): "Lichtgeel",
    (255, 250, 205): "Citroengeel",
    (250, 250, 210): "Lichtgoudgeel",
    (255, 215, 0): "Goud",
    (238, 232, 170): "Bleekgoud",
    (189, 183, 107): "Donkergoudgeel",

    # Greens
    (0, 255, 0): "Limoengroen",
    (0, 128, 0): "Groen",
    (34, 139, 34): "Bosgroen",
    (144, 238, 144): "Lichtgroen",
    (143, 188, 143): "Donker zeegroen",
    (60, 179, 113): "Medium zeegroen",
    (46, 139, 87): "Zeegroen",
    (0, 100, 0): "Donkergroen",
    (154, 205, 50): "Geelgroen",
    (124, 252, 0): "Grasgroen",
    (127, 255, 0): "Chartreuse",
    (50, 205, 50): "Lentegroen",
    (152, 251, 152): "Bleekgroen",

    # Cyans
    (0, 255, 255): "Cyaan",
    (0, 206, 209): "Donkerturkoois",
    (64, 224, 208): "Turkoois",
    (72, 209, 204): "Medium turkoois",
    (175, 238, 238): "Bleekturkoois",
    (127, 255, 212): "Aquamarijn",
    (176, 224, 230): "Poederblauw",
    (95, 158, 160): "Cadet blauw",

    # Blues
    (0, 0, 255): "Blauw",
    (0, 0, 139): "Donkerblauw",
    (0, 0, 205): "Medium blauw",
    (25, 25, 112): "Middernachtblauw",
    (0, 191, 255): "Diep hemelsblauw",
    (30, 144, 255): "Dodger blauw",
    (100, 149, 237): "Korenbloemblauw",
    (70, 130, 180): "Staalblauw",
    (135, 206, 235): "Hemelsblauw",
    (135, 206, 250): "Licht hemelsblauw",
    (173, 216, 230): "Lichtblauw",
    (176, 196, 222): "Licht staalblauw",

    # Purples/Violets
    (128, 0, 128): "Paars",
    (75, 0, 130): "Indigo",
    (138, 43, 226): "Blauwviolet",
    (147, 112, 219): "Medium paars",
    (153, 50, 204): "Donker orchidee",
    (186, 85, 211): "Medium orchidee",
    (218, 112, 214): "Orchidee",
    (221, 160, 221): "Pruim",
    (238, 130, 238): "Violet",
    (216, 191, 216): "Distel",
    (255, 0, 255): "Magenta",

    # Pinks
    (255, 192, 203): "Roze",
    (255, 182, 193): "Lichtroze",
    (255, 105, 180): "Heet roze",
    (255, 20, 147): "Diep roze",
    (219, 112, 147): "Bleek violet rood",

    # Browns
    (165, 42, 42): "Bruin",
    (139, 69, 19): "Zadelbruin",
    (160, 82, 45): "Sienna",
    (205, 133, 63): "Peru",
    (210, 105, 30): "Chocoladebruin",
    (222, 184, 135): "Mocca",
    (244, 164, 96): "Zandbruin",
    (210, 180, 140): "Tan",
    (188, 143, 143): "Roze bruin",

    # Grays/Whites/Blacks
    (0, 0, 0): "Zwart",
    (105, 105, 105): "Donkergrijs",
    (128, 128, 128): "Grijs",
    (169, 169, 169): "Donker lichtgrijs",
    (192, 192, 192): "Zilver",
    (211, 211, 211): "Lichtgrijs",
    (220, 220, 220): "Gainsboro",
    (245, 245, 245): "Witgrijs",
    (255, 255, 255): "Wit",
    (240, 248, 255): "Alice blauw",
    (245, 245, 220): "Beige",
    (255, 228, 196): "Bisque",
    (255, 235, 205): "Blancheeramandel",
    (245, 222, 179): "Tarwe",
    (255, 248, 220): "Maïsgeel",
    (255, 250, 240): "Bloemenwitgeel",
    (250, 240, 230): "Linnen",
    (253, 245, 230): "Oude kant",
    (255, 239, 213): "Papaja room",
    (255, 245, 238): "Zeestaartgeel",
    (240, 255, 240): "Honingdauw",
    (255, 240, 245): "Lavendel blos",
    (240, 255, 255): "Azuurblauw",
    (255, 250, 250): "Sneeuwwit",
    (240, 248, 255): "Spookwit",
    (245, 255, 250): "Mintroom",
    (255, 255, 240): "Ivoor",
}


class SmartColorNamer:
    """Intelligent color naming using distance algorithms"""

    def __init__(self):
        """Initialize smart color namer"""
        self.color_db = COLOR_NAMES_DB
        # Pre-compute RGB arrays for vectorized operations
        self.db_colors_array = np.array(list(self.color_db.keys()), dtype=np.float32)
        self.db_names = list(self.color_db.values())

    def get_color_name(self, rgb: Tuple[int, int, int],
                       suggest_alternatives: bool = True) -> Dict[str, any]:
        """
        Get intelligent name for RGB color

        Args:
            rgb: Tuple of (r, g, b) values (0-255)
            suggest_alternatives: Whether to suggest alternative names

        Returns:
            Dict with 'name', 'confidence', 'alternatives', 'description'
        """
        r, g, b = rgb

        # Find nearest color in database
        color_array = np.array([r, g, b], dtype=np.float32)
        distances = np.sqrt(np.sum((self.db_colors_array - color_array) ** 2, axis=1))

        # Get best match
        best_idx = np.argmin(distances)
        best_distance = distances[best_idx]
        best_name = self.db_names[best_idx]

        # Calculate confidence (closer = more confident)
        # Max distance in RGB space is ~441 (sqrt(255^2 * 3))
        confidence = max(0.0, 1.0 - (best_distance / 441.0))

        # Get alternative names (next 3 closest)
        alternatives = []
        if suggest_alternatives:
            sorted_indices = np.argsort(distances)
            for idx in sorted_indices[1:4]:  # Skip first (best match)
                alt_name = self.db_names[idx]
                alt_distance = distances[idx]
                alt_confidence = max(0.0, 1.0 - (alt_distance / 441.0))
                if alt_confidence > 0.5:  # Only suggest if reasonably close
                    alternatives.append({
                        'name': alt_name,
                        'confidence': round(alt_confidence, 2)
                    })

        # Generate descriptive text based on HSL
        description = self._generate_description(rgb)

        return {
            'name': best_name,
            'confidence': round(confidence, 2),
            'alternatives': alternatives,
            'description': description,
            'rgb': rgb
        }

    def _generate_description(self, rgb: Tuple[int, int, int]) -> str:
        """Generate descriptive text for color"""
        r, g, b = [x / 255.0 for x in rgb]
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        # Convert hue to degrees
        h_deg = h * 360

        # Determine base color
        if s < 0.1:
            if l < 0.2:
                base = "heel donker grijs"
            elif l < 0.4:
                base = "donkergrijs"
            elif l < 0.6:
                base = "middengrijs"
            elif l < 0.8:
                base = "lichtgrijs"
            else:
                base = "zeer lichtgrijs"
        else:
            # Chromatic color
            if h_deg < 15 or h_deg >= 345:
                base = "rood"
            elif h_deg < 45:
                base = "oranje"
            elif h_deg < 75:
                base = "geel"
            elif h_deg < 150:
                base = "groen"
            elif h_deg < 200:
                base = "cyaan"
            elif h_deg < 260:
                base = "blauw"
            elif h_deg < 300:
                base = "paars"
            else:
                base = "magenta"

            # Add lightness modifier
            if l < 0.3:
                base = f"donker {base}"
            elif l > 0.7:
                base = f"licht {base}"

            # Add saturation modifier
            if s < 0.4:
                base = f"gedempt {base}"
            elif s > 0.8:
                base = f"levendig {base}"

        return base

    def suggest_names_for_palette(self, colors: List[Tuple[int, int, int]]) -> List[Dict]:
        """
        Suggest names for a color palette with context awareness

        Args:
            colors: List of RGB tuples

        Returns:
            List of name suggestion dicts
        """
        suggestions = []

        for i, color in enumerate(colors):
            result = self.get_color_name(color, suggest_alternatives=True)

            # Add palette position info
            result['palette_index'] = i + 1
            result['palette_total'] = len(colors)

            suggestions.append(result)

        return suggestions

    def get_contrasting_name(self, base_rgb: Tuple[int, int, int]) -> str:
        """Get name for color that contrasts with base color"""
        # Calculate complementary color (opposite on color wheel)
        r, g, b = [x / 255.0 for x in base_rgb]
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        # Complementary hue (180 degrees opposite)
        h_comp = (h + 0.5) % 1.0

        # Convert back to RGB
        r_comp, g_comp, b_comp = colorsys.hls_to_rgb(h_comp, l, s)
        rgb_comp = (int(r_comp * 255), int(g_comp * 255), int(b_comp * 255))

        # Get name for complementary color
        result = self.get_color_name(rgb_comp, suggest_alternatives=False)
        return result['name']


# Global singleton instance
_namer_instance = None

def get_smart_namer() -> SmartColorNamer:
    """Get or create global smart color namer instance"""
    global _namer_instance
    if _namer_instance is None:
        _namer_instance = SmartColorNamer()
        logger.info("Smart color namer initialized with {} known colors".format(
            len(_namer_instance.color_db)))
    return _namer_instance
