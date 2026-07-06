// Advanced contour tracing algorithms for precise line drawing

class ContourTracer {
    constructor() {
        // Marching squares lookup table for contour directions
        // Each index represents a 2x2 cell configuration (4 bits)
        // Each value is an array of line segments [x1, y1, x2, y2]
        this.marchingSquaresTable = [
            [], // 0: no edges
            [[0, 0.5, 0.5, 1]], // 1: bottom-left corner
            [[0.5, 1, 1, 0.5]], // 2: bottom-right corner
            [[0, 0.5, 1, 0.5]], // 3: bottom edge
            [[0.5, 0, 1, 0.5]], // 4: top-right corner
            [[0, 0.5, 0.5, 0], [0.5, 1, 1, 0.5]], // 5: saddle point (ambiguous)
            [[0.5, 0, 0.5, 1]], // 6: right edge
            [[0, 0.5, 0.5, 0]], // 7: bottom-left to top-right
            [[0, 0.5, 0.5, 0]], // 8: top-left corner
            [[0.5, 0, 0.5, 1]], // 9: left edge
            [[0, 0.5, 0.5, 1], [0.5, 0, 1, 0.5]], // 10: saddle point (ambiguous)
            [[0.5, 0, 1, 0.5]], // 11: top-left to bottom-right
            [[0, 0.5, 1, 0.5]], // 12: top edge
            [[0.5, 1, 1, 0.5]], // 13: top-left to bottom-left
            [[0, 0.5, 0.5, 1]], // 14: top-left to top-right
            [] // 15: no edges
        ];
    }

    /**
     * Trace contours using Marching Squares algorithm
     * Returns smooth contour paths for each color boundary
     */
    traceContours(colorMap, width, height) {
        const contours = [];
        const visited = new Set();

        // Find all boundary edges using marching squares
        for (let y = 0; y < height - 1; y++) {
            for (let x = 0; x < width - 1; x++) {
                const cellIndex = this.getMarchingSquaresIndex(colorMap, x, y, width, height);

                if (cellIndex === 0 || cellIndex === 15) continue; // No boundary

                const segments = this.marchingSquaresTable[cellIndex];

                for (let segment of segments) {
                    const [x1, y1, x2, y2] = segment;
                    const contour = {
                        points: [
                            { x: x + x1, y: y + y1 },
                            { x: x + x2, y: y + y2 }
                        ]
                    };
                    contours.push(contour);
                }
            }
        }

        // Merge connected segments into continuous paths
        const mergedContours = this.mergeContourSegments(contours);

        return mergedContours;
    }

    /**
     * Get marching squares cell index based on color differences
     */
    getMarchingSquaresIndex(colorMap, x, y, width, height) {
        // Get colors of 2x2 cell
        const c1 = colorMap[y * width + x];           // top-left
        const c2 = colorMap[y * width + (x + 1)];     // top-right
        const c3 = colorMap[(y + 1) * width + x];     // bottom-left
        const c4 = colorMap[(y + 1) * width + (x + 1)]; // bottom-right

        // Use the most common color as reference
        const colors = [c1, c2, c3, c4];
        const colorCounts = {};
        for (let c of colors) {
            colorCounts[c] = (colorCounts[c] || 0) + 1;
        }
        const refColor = Object.keys(colorCounts).reduce((a, b) =>
            colorCounts[a] > colorCounts[b] ? a : b
        );

        // Create binary index based on whether each corner matches reference
        let index = 0;
        if (c1 !== refColor) index |= 1;  // bit 0
        if (c2 !== refColor) index |= 2;  // bit 1
        if (c3 !== refColor) index |= 4;  // bit 2
        if (c4 !== refColor) index |= 8;  // bit 3

        return index;
    }

    /**
     * Merge disconnected contour segments into continuous paths
     */
    mergeContourSegments(contours) {
        if (contours.length === 0) return [];

        const paths = [];
        const used = new Set();
        const epsilon = 0.5; // Distance threshold for connecting segments

        for (let i = 0; i < contours.length; i++) {
            if (used.has(i)) continue;

            const path = [...contours[i].points];
            used.add(i);
            let changed = true;

            // Keep trying to extend the path
            while (changed) {
                changed = false;

                for (let j = 0; j < contours.length; j++) {
                    if (used.has(j)) continue;

                    const segment = contours[j].points;
                    const pathStart = path[0];
                    const pathEnd = path[path.length - 1];
                    const segStart = segment[0];
                    const segEnd = segment[segment.length - 1];

                    // Check if segment connects to path start
                    if (this.distance(pathStart, segEnd) < epsilon) {
                        path.unshift(...segment.slice(0, -1));
                        used.add(j);
                        changed = true;
                    }
                    // Check if segment connects to path end
                    else if (this.distance(pathEnd, segStart) < epsilon) {
                        path.push(...segment.slice(1));
                        used.add(j);
                        changed = true;
                    }
                    // Check if segment connects reversed to path start
                    else if (this.distance(pathStart, segStart) < epsilon) {
                        path.unshift(...segment.slice(1).reverse());
                        used.add(j);
                        changed = true;
                    }
                    // Check if segment connects reversed to path end
                    else if (this.distance(pathEnd, segEnd) < epsilon) {
                        path.push(...segment.slice(0, -1).reverse());
                        used.add(j);
                        changed = true;
                    }
                }
            }

            if (path.length >= 2) {
                paths.push(path);
            }
        }

        return paths;
    }

    /**
     * Ramer-Douglas-Peucker algorithm for line simplification
     * Reduces number of points while preserving shape
     */
    simplifyPath(points, epsilon = 1.0) {
        if (points.length <= 2) return points;

        // Find the point with maximum distance from line between first and last
        let maxDist = 0;
        let maxIndex = 0;
        const first = points[0];
        const last = points[points.length - 1];

        for (let i = 1; i < points.length - 1; i++) {
            const dist = this.perpendicularDistance(points[i], first, last);
            if (dist > maxDist) {
                maxDist = dist;
                maxIndex = i;
            }
        }

        // If max distance is greater than epsilon, recursively simplify
        if (maxDist > epsilon) {
            const left = this.simplifyPath(points.slice(0, maxIndex + 1), epsilon);
            const right = this.simplifyPath(points.slice(maxIndex), epsilon);

            // Concatenate results (avoiding duplicate middle point)
            return [...left.slice(0, -1), ...right];
        } else {
            // All points are close enough to the line, return endpoints
            return [first, last];
        }
    }

    /**
     * Calculate perpendicular distance from point to line
     */
    perpendicularDistance(point, lineStart, lineEnd) {
        const dx = lineEnd.x - lineStart.x;
        const dy = lineEnd.y - lineStart.y;
        const lineLengthSquared = dx * dx + dy * dy;

        if (lineLengthSquared === 0) {
            return this.distance(point, lineStart);
        }

        const t = Math.max(0, Math.min(1,
            ((point.x - lineStart.x) * dx + (point.y - lineStart.y) * dy) / lineLengthSquared
        ));

        const projection = {
            x: lineStart.x + t * dx,
            y: lineStart.y + t * dy
        };

        return this.distance(point, projection);
    }

    /**
     * Catmull-Rom spline interpolation for smooth curves
     * Creates a smooth curve through all control points
     */
    smoothPathWithSpline(points, segmentsPerPoint = 8) {
        if (points.length < 2) return points;
        if (points.length === 2) return points;

        const smoothPoints = [];

        // Add first point
        smoothPoints.push(points[0]);

        // For each segment between points
        for (let i = 0; i < points.length - 1; i++) {
            const p0 = points[Math.max(0, i - 1)];
            const p1 = points[i];
            const p2 = points[i + 1];
            const p3 = points[Math.min(points.length - 1, i + 2)];

            // Generate interpolated points using Catmull-Rom
            for (let t = 0; t < 1; t += 1 / segmentsPerPoint) {
                const point = this.catmullRomSpline(p0, p1, p2, p3, t);
                smoothPoints.push(point);
            }
        }

        // Add last point
        smoothPoints.push(points[points.length - 1]);

        return smoothPoints;
    }

    /**
     * Catmull-Rom spline calculation
     */
    catmullRomSpline(p0, p1, p2, p3, t) {
        const t2 = t * t;
        const t3 = t2 * t;

        const x = 0.5 * (
            (2 * p1.x) +
            (-p0.x + p2.x) * t +
            (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
            (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3
        );

        const y = 0.5 * (
            (2 * p1.y) +
            (-p0.y + p2.y) * t +
            (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
            (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3
        );

        return { x, y };
    }

    /**
     * Alternative: Chaikin's corner cutting algorithm for smoothing
     * Simpler and faster than splines, but effective
     * Now with corner preservation!
     */
    smoothPathChaikin(points, iterations = 2, cornerAngleThreshold = 120) {
        if (points.length < 3) return points;

        // Detect corners first
        const corners = this.detectCorners(points, cornerAngleThreshold);

        let smoothed = [...points];

        for (let iter = 0; iter < iterations; iter++) {
            const newPoints = [];

            // Keep first point
            newPoints.push(smoothed[0]);

            // Apply corner cutting
            for (let i = 0; i < smoothed.length - 1; i++) {
                const p1 = smoothed[i];
                const p2 = smoothed[i + 1];

                // Check if this is a corner point (should be preserved)
                const isCorner = corners.has(i);

                if (isCorner) {
                    // Preserve corners - don't smooth them
                    newPoints.push(p1);
                    newPoints.push(p2);
                } else {
                    // Create two new points at 1/4 and 3/4 along the segment
                    newPoints.push({
                        x: 0.75 * p1.x + 0.25 * p2.x,
                        y: 0.75 * p1.y + 0.25 * p2.y
                    });
                    newPoints.push({
                        x: 0.25 * p1.x + 0.75 * p2.x,
                        y: 0.25 * p1.y + 0.75 * p2.y
                    });
                }
            }

            // Keep last point
            newPoints.push(smoothed[smoothed.length - 1]);

            smoothed = newPoints;
        }

        return smoothed;
    }

    /**
     * Detect corners in a path based on angle threshold
     * Returns a Set of indices where corners are detected
     */
    detectCorners(points, angleThreshold = 120) {
        const corners = new Set();

        if (points.length < 3) return corners;

        // Convert angle threshold to radians
        const thresholdRad = (angleThreshold * Math.PI) / 180;

        for (let i = 1; i < points.length - 1; i++) {
            const p0 = points[i - 1];
            const p1 = points[i];
            const p2 = points[i + 1];

            // Calculate vectors
            const v1 = { x: p1.x - p0.x, y: p1.y - p0.y };
            const v2 = { x: p2.x - p1.x, y: p2.y - p1.y };

            // Calculate angle between vectors using dot product
            const dot = v1.x * v2.x + v1.y * v2.y;
            const len1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y);
            const len2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y);

            if (len1 === 0 || len2 === 0) continue;

            const cosAngle = dot / (len1 * len2);
            const angle = Math.acos(Math.max(-1, Math.min(1, cosAngle)));

            // If angle is sharp (less than threshold), mark as corner
            if (angle < thresholdRad) {
                corners.add(i);
            }
        }

        return corners;
    }

    /**
     * Distance between two points
     */
    distance(p1, p2) {
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    /**
     * Trace clean contours directly from color boundaries
     * This is the main method to use for the Paint-by-Numbers app
     */
    traceColorBoundaries(colorMap, width, height, options = {}) {
        const {
            simplifyEpsilon = 1.0,
            smoothingIterations = 2,
            useCatmullRom = false,
            segmentsPerPoint = 6,
            cornerAngleThreshold = 120  // Preserve corners sharper than this angle
        } = options;

        // Step 1: Extract raw boundary pixels
        const boundaries = this.extractBoundaryPixels(colorMap, width, height);

        // Step 2: Convert to connected paths
        const paths = this.boundaryPixelsToPaths(boundaries);

        // Step 3: Simplify paths
        const simplifiedPaths = paths.map(path =>
            this.simplifyPath(path, simplifyEpsilon)
        );

        // Step 4: Smooth paths with corner preservation
        const smoothedPaths = simplifiedPaths.map(path => {
            if (useCatmullRom) {
                return this.smoothPathWithSpline(path, segmentsPerPoint);
            } else {
                return this.smoothPathChaikin(path, smoothingIterations, cornerAngleThreshold);
            }
        });

        return smoothedPaths;
    }

    /**
     * Extract boundary pixels between different colors
     */
    extractBoundaryPixels(colorMap, width, height) {
        const boundaries = [];

        for (let y = 0; y < height - 1; y++) {
            for (let x = 0; x < width - 1; x++) {
                const idx = y * width + x;
                const currentColor = colorMap[idx];

                // Check right neighbor
                const rightColor = colorMap[idx + 1];
                if (currentColor !== rightColor) {
                    boundaries.push({
                        x: x + 0.5,
                        y: y,
                        direction: 'vertical'
                    });
                }

                // Check bottom neighbor
                const bottomColor = colorMap[idx + width];
                if (currentColor !== bottomColor) {
                    boundaries.push({
                        x: x,
                        y: y + 0.5,
                        direction: 'horizontal'
                    });
                }
            }
        }

        return boundaries;
    }

    /**
     * Convert boundary pixels to connected paths
     */
    boundaryPixelsToPaths(boundaries) {
        // Group boundaries by their approximate position to form paths
        // This is a simplified version - could be improved with proper path tracing
        const paths = [];
        const epsilon = 1.5;
        const used = new Set();

        for (let i = 0; i < boundaries.length; i++) {
            if (used.has(i)) continue;

            const path = [{ x: boundaries[i].x, y: boundaries[i].y }];
            used.add(i);

            // Try to extend path by finding nearby boundaries
            let extended = true;
            while (extended) {
                extended = false;
                const lastPoint = path[path.length - 1];

                for (let j = 0; j < boundaries.length; j++) {
                    if (used.has(j)) continue;

                    const point = { x: boundaries[j].x, y: boundaries[j].y };
                    const dist = this.distance(lastPoint, point);

                    if (dist < epsilon) {
                        path.push(point);
                        used.add(j);
                        extended = true;
                        break;
                    }
                }
            }

            if (path.length >= 2) {
                paths.push(path);
            }
        }

        return paths;
    }
}
