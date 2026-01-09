// Color utilities for intelligent naming and merging

/**
 * Get intelligent color name based on RGB values
 * Uses HSV color space for better color categorization
 */
function getColorName(r, g, b) {
    // Convert RGB to HSV
    const { h, s, v } = rgbToHsv(r, g, b);

    // Handle grayscale colors (low saturation)
    if (s < 0.15) {
        if (v < 0.2) return 'Zwart';
        if (v > 0.85) return 'Wit';
        if (v > 0.6) return 'Lichtgrijs';
        if (v > 0.4) return 'Grijs';
        return 'Donkergrijs';
    }

    // Determine base color from hue
    let baseName = '';

    if (h >= 345 || h < 15) {
        baseName = 'Rood';
    } else if (h >= 15 && h < 45) {
        baseName = s > 0.6 ? 'Oranje' : 'Bruin';
    } else if (h >= 45 && h < 70) {
        baseName = 'Geel';
    } else if (h >= 70 && h < 150) {
        baseName = 'Groen';
    } else if (h >= 150 && h < 200) {
        baseName = 'Cyaan';
    } else if (h >= 200 && h < 260) {
        baseName = 'Blauw';
    } else if (h >= 260 && h < 290) {
        baseName = 'Paars';
    } else if (h >= 290 && h < 320) {
        baseName = 'Magenta';
    } else {
        baseName = 'Roze';
    }

    // Add brightness modifier
    let modifier = '';
    if (v < 0.4) {
        modifier = 'Donker';
    } else if (v > 0.8 && s < 0.4) {
        modifier = 'Licht';
    } else if (s > 0.8 && v > 0.7) {
        modifier = 'Fel';
    }

    // Special cases
    if (baseName === 'Bruin' && v < 0.3) {
        return 'Donkerbruin';
    }
    if (baseName === 'Geel' && v < 0.5) {
        return 'Oker';
    }
    if (baseName === 'Oranje' && v < 0.4) {
        return 'Bruin';
    }

    return modifier ? `${modifier} ${baseName.toLowerCase()}` : baseName;
}

/**
 * Convert RGB to HSV color space
 */
function rgbToHsv(r, g, b) {
    r /= 255;
    g /= 255;
    b /= 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const diff = max - min;

    let h = 0;
    let s = max === 0 ? 0 : diff / max;
    let v = max;

    if (diff !== 0) {
        if (max === r) {
            h = ((g - b) / diff + (g < b ? 6 : 0)) * 60;
        } else if (max === g) {
            h = ((b - r) / diff + 2) * 60;
        } else {
            h = ((r - g) / diff + 4) * 60;
        }
    }

    return { h, s, v };
}

/**
 * Calculate color distance (Delta E approximation)
 * Returns value between 0 (identical) and ~764 (max different)
 */
function colorDistance(r1, g1, b1, r2, g2, b2) {
    // Simple Euclidean distance in RGB space
    // For better accuracy, could use LAB color space, but this is faster
    const dr = r1 - r2;
    const dg = g1 - g2;
    const db = b1 - b2;

    // Weighted formula that accounts for human perception
    const rmean = (r1 + r2) / 2;
    const r = dr * dr * (2 + rmean / 256);
    const g = dg * dg * 4;
    const b = db * db * (2 + (255 - rmean) / 256);

    return Math.sqrt(r + g + b);
}

/**
 * Merge similar colors in a color array
 * Returns array of merged colors with fewer duplicates
 */
function mergeSimilarColors(colors, threshold = 30) {
    if (!colors || colors.length === 0) return [];

    const merged = [];
    const used = new Array(colors.length).fill(false);

    for (let i = 0; i < colors.length; i++) {
        if (used[i]) continue;

        const color1 = colors[i];
        const similar = [color1];
        used[i] = true;

        // Find all similar colors
        for (let j = i + 1; j < colors.length; j++) {
            if (used[j]) continue;

            const color2 = colors[j];
            const dist = colorDistance(
                color1.r, color1.g, color1.b,
                color2.r, color2.g, color2.b
            );

            if (dist < threshold) {
                similar.push(color2);
                used[j] = true;
            }
        }

        // Average all similar colors
        const avgR = Math.round(similar.reduce((sum, c) => sum + c.r, 0) / similar.length);
        const avgG = Math.round(similar.reduce((sum, c) => sum + c.g, 0) / similar.length);
        const avgB = Math.round(similar.reduce((sum, c) => sum + c.b, 0) / similar.length);

        merged.push({
            r: avgR,
            g: avgG,
            b: avgB,
            hex: rgbToHex(avgR, avgG, avgB),
            count: similar.length
        });
    }

    console.log(`Merged ${colors.length} colors into ${merged.length} distinct colors`);
    return merged;
}

/**
 * Post-process detected colors:
 * 1. Merge similar colors
 * 2. Add intelligent names
 * 3. Sort by brightness or hue
 */
function processDetectedColors(colors, mergeThreshold = 30, sortBy = 'brightness') {
    // First merge similar colors
    let processed = mergeSimilarColors(colors, mergeThreshold);

    // Add intelligent names
    processed = processed.map(color => ({
        ...color,
        name: getColorName(color.r, color.g, color.b)
    }));

    // Sort colors
    if (sortBy === 'brightness') {
        processed.sort((a, b) => {
            const brightnessA = 0.299 * a.r + 0.587 * a.g + 0.114 * a.b;
            const brightnessB = 0.299 * b.r + 0.587 * b.g + 0.114 * b.b;
            return brightnessB - brightnessA; // Descending
        });
    } else if (sortBy === 'hue') {
        processed.sort((a, b) => {
            const hsvA = rgbToHsv(a.r, a.g, a.b);
            const hsvB = rgbToHsv(b.r, b.g, b.b);
            return hsvA.h - hsvB.h;
        });
    }

    return processed;
}

/**
 * Check if colors are too similar (should be merged)
 */
function areColorsSimilar(color1, color2, threshold = 30) {
    return colorDistance(
        color1.r, color1.g, color1.b,
        color2.r, color2.g, color2.b
    ) < threshold;
}

/**
 * Get color suggestions based on common paint colors
 */
function getColorSuggestions() {
    return [
        { name: 'Zwart', hex: '#000000', r: 0, g: 0, b: 0 },
        { name: 'Wit', hex: '#FFFFFF', r: 255, g: 255, b: 255 },
        { name: 'Rood', hex: '#FF0000', r: 255, g: 0, b: 0 },
        { name: 'Blauw', hex: '#0000FF', r: 0, g: 0, b: 255 },
        { name: 'Geel', hex: '#FFFF00', r: 255, g: 255, b: 0 },
        { name: 'Groen', hex: '#00FF00', r: 0, g: 255, b: 0 },
        { name: 'Oranje', hex: '#FF8800', r: 255, g: 136, b: 0 },
        { name: 'Paars', hex: '#8800FF', r: 136, g: 0, b: 255 },
        { name: 'Roze', hex: '#FF00FF', r: 255, g: 0, b: 255 },
        { name: 'Bruin', hex: '#8B4513', r: 139, g: 69, b: 19 },
        { name: 'Grijs', hex: '#808080', r: 128, g: 128, b: 128 }
    ];
}
