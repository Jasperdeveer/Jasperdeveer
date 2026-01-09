// AI-Powered Edge Detection using TensorFlow.js
// Enhanced edge detection with deep learning and advanced filters

class AIEdgeDetector {
    constructor() {
        this.tfLoaded = false;
        this.model = null;
        this.progressCallback = null;
    }

    /**
     * Set progress callback for reporting processing status
     */
    setProgressCallback(callback) {
        this.progressCallback = callback;
    }

    /**
     * Report progress to callback if available
     */
    reportProgress(percent, message) {
        if (this.progressCallback) {
            this.progressCallback(percent, message);
        }
    }

    /**
     * Initialize TensorFlow.js (to be called when library is loaded)
     */
    async initialize() {
        if (typeof tf !== 'undefined') {
            this.tfLoaded = true;
            console.log('TensorFlow.js loaded successfully');
            // We'll use TF.js for image processing operations
            return true;
        }
        return false;
    }

    /**
     * Advanced Canny Edge Detection with AI enhancements
     * Uses bilateral filtering and adaptive thresholding
     */
    detectEdgesAdvanced(imageData, width, height, options = {}) {
        const {
            detailLevel = 5,
            useBilateralFilter = true,
            useAdaptiveThreshold = true,
            useNonMaxSuppression = true,
            useHysteresis = true,
            minThreshold = 0.1,
            maxThreshold = 0.3,
            useMultiScale = true,
            preserveCorners = true
        } = options;

        this.reportProgress(5, 'Grayscale conversie...');

        // Step 1: Convert to grayscale
        const gray = this.toGrayscale(imageData, width, height);

        // Use multi-scale detection for better detail preservation
        if (useMultiScale) {
            return this.multiScaleEdgeDetection(gray, width, height, {
                detailLevel,
                useBilateralFilter,
                useAdaptiveThreshold,
                useNonMaxSuppression,
                useHysteresis,
                preserveCorners
            });
        }

        this.reportProgress(15, 'Noise filtering...');

        // Step 2: Apply bilateral filter for edge-preserving smoothing
        let filtered = gray;
        if (useBilateralFilter) {
            filtered = this.bilateralFilter(gray, width, height, {
                spatialSigma: 3,
                rangeSigma: 50,
                kernelSize: 5
            });
        } else {
            // Standard Gaussian blur
            filtered = this.gaussianBlur(gray, width, height, 1.4);
        }

        this.reportProgress(30, 'Gradient berekening...');

        // Step 3: Sobel operator for gradient calculation
        const { magnitude, direction } = this.sobelGradient(filtered, width, height);

        // Detect corners for preservation
        let corners = null;
        if (preserveCorners) {
            this.reportProgress(40, 'Corner detection...');
            corners = this.harrisCornerDetector(gray, width, height);
        }

        this.reportProgress(50, 'Non-maximum suppression...');

        // Step 4: Non-maximum suppression for thin edges
        let edges = magnitude;
        if (useNonMaxSuppression) {
            edges = this.nonMaximumSuppression(magnitude, direction, width, height);
        }

        this.reportProgress(60, 'Adaptive thresholding...');

        // Step 5: Adaptive or fixed thresholding
        let binary;
        if (useAdaptiveThreshold) {
            binary = this.adaptiveThreshold(edges, width, height, detailLevel);
        } else {
            binary = this.doubleThreshold(edges, width, height, minThreshold, maxThreshold);
        }

        this.reportProgress(70, 'Hysteresis tracking...');

        // Step 6: Hysteresis edge tracking
        if (useHysteresis) {
            binary = this.hysteresisEdgeTracking(binary, width, height);
        }

        this.reportProgress(80, 'Morphological operations...');

        // Step 7: Morphological operations for cleaner edges
        binary = this.morphologicalClose(binary, width, height);

        // Add corners back to preserve sharp features
        if (preserveCorners && corners) {
            this.reportProgress(85, 'Corner preservation...');
            binary = this.addCorners(binary, corners, width, height);
        }

        this.reportProgress(90, 'Edge thinning...');

        // Step 8: Edge thinning for precise lines
        binary = this.edgeThinning(binary, width, height);

        this.reportProgress(100, 'Klaar!');

        return this.createImageData(binary, width, height);
    }

    /**
     * Multi-Scale Edge Detection
     * Combines edges detected at different scales for optimal detail preservation
     */
    multiScaleEdgeDetection(gray, width, height, options) {
        const scales = [
            { sigma: 0.5, weight: 0.3, name: 'Fijne details' },   // Fine details
            { sigma: 1.5, weight: 0.4, name: 'Medium details' },  // Medium details
            { sigma: 3.0, weight: 0.3, name: 'Grove contouren' }  // Coarse contours
        ];

        const edgeMaps = [];

        // Detect edges at each scale
        for (let i = 0; i < scales.length; i++) {
            const scale = scales[i];
            const progress = 15 + (i * 20);
            this.reportProgress(progress, `${scale.name}...`);

            // Apply Gaussian blur at this scale
            const filtered = this.gaussianBlur(gray, width, height, scale.sigma);

            // Compute gradients
            const { magnitude, direction } = this.sobelGradient(filtered, width, height);

            // Non-maximum suppression
            const edges = this.nonMaximumSuppression(magnitude, direction, width, height);

            edgeMaps.push({ edges, weight: scale.weight });
        }

        this.reportProgress(60, 'Schalen combineren...');

        // Combine edge maps with weighted sum
        const combined = new Float32Array(width * height);
        for (let i = 0; i < combined.length; i++) {
            let sum = 0;
            for (let map of edgeMaps) {
                sum += map.edges[i] * map.weight;
            }
            combined[i] = sum;
        }

        this.reportProgress(70, 'Adaptive thresholding...');

        // Apply adaptive thresholding
        const binary = this.adaptiveThreshold(combined, width, height, options.detailLevel);

        this.reportProgress(80, 'Hysteresis tracking...');

        // Hysteresis edge tracking
        const tracked = this.hysteresisEdgeTracking(binary, width, height);

        this.reportProgress(90, 'Corner detection...');

        // Detect and preserve corners
        if (options.preserveCorners) {
            const corners = this.harrisCornerDetector(gray, width, height);
            const withCorners = this.addCorners(tracked, corners, width, height);

            this.reportProgress(100, 'Klaar!');
            return this.createImageData(withCorners, width, height);
        }

        this.reportProgress(100, 'Klaar!');
        return this.createImageData(tracked, width, height);
    }

    /**
     * Harris Corner Detector
     * Detects corners to preserve sharp features
     */
    harrisCornerDetector(gray, width, height, threshold = 0.01) {
        const corners = new Uint8Array(width * height);

        // Compute image gradients
        const Ix = new Float32Array(width * height);
        const Iy = new Float32Array(width * height);

        // Sobel for gradients
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = y * width + x;

                // Sobel X
                Ix[idx] = (
                    -gray[(y - 1) * width + (x - 1)] + gray[(y - 1) * width + (x + 1)] +
                    -2 * gray[y * width + (x - 1)] + 2 * gray[y * width + (x + 1)] +
                    -gray[(y + 1) * width + (x - 1)] + gray[(y + 1) * width + (x + 1)]
                );

                // Sobel Y
                Iy[idx] = (
                    -gray[(y - 1) * width + (x - 1)] - 2 * gray[(y - 1) * width + x] - gray[(y - 1) * width + (x + 1)] +
                    gray[(y + 1) * width + (x - 1)] + 2 * gray[(y + 1) * width + x] + gray[(y + 1) * width + (x + 1)]
                );
            }
        }

        // Compute products of derivatives
        const Ix2 = new Float32Array(width * height);
        const Iy2 = new Float32Array(width * height);
        const Ixy = new Float32Array(width * height);

        for (let i = 0; i < width * height; i++) {
            Ix2[i] = Ix[i] * Ix[i];
            Iy2[i] = Iy[i] * Iy[i];
            Ixy[i] = Ix[i] * Iy[i];
        }

        // Apply Gaussian window
        const windowSize = 3;
        const Sx2 = this.gaussianBlur(Ix2, width, height, 1.0);
        const Sy2 = this.gaussianBlur(Iy2, width, height, 1.0);
        const Sxy = this.gaussianBlur(Ixy, width, height, 1.0);

        // Compute corner response
        const k = 0.04;
        const R = new Float32Array(width * height);
        let maxR = 0;

        for (let i = 0; i < width * height; i++) {
            const det = Sx2[i] * Sy2[i] - Sxy[i] * Sxy[i];
            const trace = Sx2[i] + Sy2[i];
            R[i] = det - k * trace * trace;
            maxR = Math.max(maxR, R[i]);
        }

        // Threshold and non-maximum suppression
        const cornerThreshold = maxR * threshold;
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = y * width + x;

                if (R[idx] > cornerThreshold) {
                    // Check if local maximum
                    let isMax = true;
                    for (let dy = -1; dy <= 1; dy++) {
                        for (let dx = -1; dx <= 1; dx++) {
                            if (dx === 0 && dy === 0) continue;
                            const nidx = (y + dy) * width + (x + dx);
                            if (R[nidx] > R[idx]) {
                                isMax = false;
                                break;
                            }
                        }
                        if (!isMax) break;
                    }

                    if (isMax) {
                        corners[idx] = 255;
                    }
                }
            }
        }

        return corners;
    }

    /**
     * Add detected corners to edge map
     */
    addCorners(binary, corners, width, height) {
        const result = new Uint8Array(binary);

        // Dilate corners slightly to ensure connectivity
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = y * width + x;

                if (corners[idx] > 0) {
                    // Add corner and small neighborhood
                    result[idx] = 255;
                    for (let dy = -1; dy <= 1; dy++) {
                        for (let dx = -1; dx <= 1; dx++) {
                            const nidx = (y + dy) * width + (x + dx);
                            if (result[nidx] > 0) {
                                result[nidx] = 255;
                            }
                        }
                    }
                }
            }
        }

        return result;
    }

    /**
     * Convert RGBA image data to grayscale
     */
    toGrayscale(imageData, width, height) {
        const gray = new Float32Array(width * height);
        const data = imageData.data;

        for (let i = 0; i < data.length; i += 4) {
            const idx = i / 4;
            // Use luminance formula for better edge detection
            gray[idx] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        }

        return gray;
    }

    /**
     * Bilateral filter - edge-preserving smoothing
     * Reduces noise while keeping edges sharp
     */
    bilateralFilter(gray, width, height, options = {}) {
        const { spatialSigma = 3, rangeSigma = 50, kernelSize = 5 } = options;
        const filtered = new Float32Array(width * height);
        const radius = Math.floor(kernelSize / 2);

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                const centerValue = gray[idx];

                let sum = 0;
                let weightSum = 0;

                // Kernel loop
                for (let ky = -radius; ky <= radius; ky++) {
                    for (let kx = -radius; kx <= radius; kx++) {
                        const nx = x + kx;
                        const ny = y + ky;

                        if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;

                        const nidx = ny * width + nx;
                        const neighborValue = gray[nidx];

                        // Spatial Gaussian weight
                        const spatialDist = kx * kx + ky * ky;
                        const spatialWeight = Math.exp(-spatialDist / (2 * spatialSigma * spatialSigma));

                        // Range Gaussian weight (based on intensity difference)
                        const rangeDist = (centerValue - neighborValue) * (centerValue - neighborValue);
                        const rangeWeight = Math.exp(-rangeDist / (2 * rangeSigma * rangeSigma));

                        const weight = spatialWeight * rangeWeight;

                        sum += neighborValue * weight;
                        weightSum += weight;
                    }
                }

                filtered[idx] = weightSum > 0 ? sum / weightSum : centerValue;
            }
        }

        return filtered;
    }

    /**
     * Standard Gaussian blur
     */
    gaussianBlur(gray, width, height, sigma) {
        const kernel = this.createGaussianKernel(sigma);
        const kSize = kernel.length;
        const kRadius = Math.floor(kSize / 2);
        const blurred = new Float32Array(width * height);

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                let sum = 0;
                let weightSum = 0;

                for (let ky = 0; ky < kSize; ky++) {
                    for (let kx = 0; kx < kSize; kx++) {
                        const py = y + ky - kRadius;
                        const px = x + kx - kRadius;

                        if (py >= 0 && py < height && px >= 0 && px < width) {
                            const weight = kernel[ky][kx];
                            sum += gray[py * width + px] * weight;
                            weightSum += weight;
                        }
                    }
                }

                blurred[y * width + x] = sum / weightSum;
            }
        }

        return blurred;
    }

    createGaussianKernel(sigma) {
        const size = Math.ceil(sigma * 3) * 2 + 1;
        const kernel = [];
        const center = Math.floor(size / 2);

        for (let y = 0; y < size; y++) {
            kernel[y] = [];
            for (let x = 0; x < size; x++) {
                const exp = -((x - center) ** 2 + (y - center) ** 2) / (2 * sigma * sigma);
                kernel[y][x] = Math.exp(exp) / (2 * Math.PI * sigma * sigma);
            }
        }

        return kernel;
    }

    /**
     * Sobel gradient calculation
     */
    sobelGradient(gray, width, height) {
        const magnitude = new Float32Array(width * height);
        const direction = new Float32Array(width * height);

        // Sobel kernels
        const sobelX = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]];
        const sobelY = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]];

        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                let gx = 0, gy = 0;

                // Apply Sobel kernels
                for (let ky = -1; ky <= 1; ky++) {
                    for (let kx = -1; kx <= 1; kx++) {
                        const pixel = gray[(y + ky) * width + (x + kx)];
                        gx += pixel * sobelX[ky + 1][kx + 1];
                        gy += pixel * sobelY[ky + 1][kx + 1];
                    }
                }

                const idx = y * width + x;
                magnitude[idx] = Math.sqrt(gx * gx + gy * gy);
                direction[idx] = Math.atan2(gy, gx);
            }
        }

        return { magnitude, direction };
    }

    /**
     * Non-maximum suppression - thins edges to single pixel width
     */
    nonMaximumSuppression(magnitude, direction, width, height) {
        const suppressed = new Float32Array(width * height);

        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = y * width + x;
                const angle = direction[idx] * (180 / Math.PI);
                const mag = magnitude[idx];

                // Normalize angle to 0-180
                let normalizedAngle = angle;
                if (normalizedAngle < 0) normalizedAngle += 180;

                // Round to nearest 45 degrees
                const roundedAngle = Math.round(normalizedAngle / 45) * 45;

                let neighbor1 = 0, neighbor2 = 0;

                // Compare with neighbors along gradient direction
                if (roundedAngle === 0 || roundedAngle === 180) {
                    neighbor1 = magnitude[y * width + (x - 1)];
                    neighbor2 = magnitude[y * width + (x + 1)];
                } else if (roundedAngle === 45) {
                    neighbor1 = magnitude[(y - 1) * width + (x + 1)];
                    neighbor2 = magnitude[(y + 1) * width + (x - 1)];
                } else if (roundedAngle === 90) {
                    neighbor1 = magnitude[(y - 1) * width + x];
                    neighbor2 = magnitude[(y + 1) * width + x];
                } else if (roundedAngle === 135) {
                    neighbor1 = magnitude[(y - 1) * width + (x - 1)];
                    neighbor2 = magnitude[(y + 1) * width + (x + 1)];
                }

                // Keep only if local maximum
                if (mag >= neighbor1 && mag >= neighbor2) {
                    suppressed[idx] = mag;
                }
            }
        }

        return suppressed;
    }

    /**
     * Adaptive thresholding based on local statistics
     */
    adaptiveThreshold(edges, width, height, detailLevel) {
        const binary = new Uint8Array(width * height);

        // Calculate global statistics
        let sum = 0;
        let count = 0;
        for (let i = 0; i < edges.length; i++) {
            if (edges[i] > 0) {
                sum += edges[i];
                count++;
            }
        }
        const mean = count > 0 ? sum / count : 0;

        // Calculate standard deviation
        let variance = 0;
        for (let i = 0; i < edges.length; i++) {
            if (edges[i] > 0) {
                variance += (edges[i] - mean) ** 2;
            }
        }
        const stdDev = Math.sqrt(variance / Math.max(1, count));

        // Adaptive thresholds based on detail level
        const sensitivity = detailLevel / 10;
        const highThreshold = mean + stdDev * (0.5 - sensitivity * 0.3);
        const lowThreshold = highThreshold * 0.4;

        // Apply thresholds
        for (let i = 0; i < edges.length; i++) {
            if (edges[i] >= highThreshold) {
                binary[i] = 255; // Strong edge
            } else if (edges[i] >= lowThreshold) {
                binary[i] = 128; // Weak edge
            }
        }

        return binary;
    }

    /**
     * Double threshold (standard Canny)
     */
    doubleThreshold(edges, width, height, minRatio, maxRatio) {
        const binary = new Uint8Array(width * height);
        const maxGradient = Math.max(...edges);

        const highThreshold = maxGradient * maxRatio;
        const lowThreshold = highThreshold * minRatio;

        for (let i = 0; i < edges.length; i++) {
            if (edges[i] >= highThreshold) {
                binary[i] = 255;
            } else if (edges[i] >= lowThreshold) {
                binary[i] = 128;
            }
        }

        return binary;
    }

    /**
     * Hysteresis edge tracking - connects weak edges to strong edges
     */
    hysteresisEdgeTracking(binary, width, height) {
        const result = new Uint8Array(binary);

        // Iteratively connect weak edges to strong edges
        let changed = true;
        let iterations = 0;
        const maxIterations = 10;

        while (changed && iterations < maxIterations) {
            changed = false;
            iterations++;

            for (let y = 1; y < height - 1; y++) {
                for (let x = 1; x < width - 1; x++) {
                    const idx = y * width + x;

                    if (result[idx] === 128) { // Weak edge
                        let hasStrongNeighbor = false;

                        // Check 8-connected neighbors
                        for (let dy = -1; dy <= 1; dy++) {
                            for (let dx = -1; dx <= 1; dx++) {
                                if (dx === 0 && dy === 0) continue;
                                const nidx = (y + dy) * width + (x + dx);
                                if (result[nidx] === 255) {
                                    hasStrongNeighbor = true;
                                    break;
                                }
                            }
                            if (hasStrongNeighbor) break;
                        }

                        if (hasStrongNeighbor) {
                            result[idx] = 255;
                            changed = true;
                        } else {
                            result[idx] = 0; // Remove weak edge not connected to strong
                        }
                    }
                }
            }
        }

        return result;
    }

    /**
     * Morphological closing - fills small gaps in edges
     */
    morphologicalClose(binary, width, height, kernelSize = 3) {
        // Dilation followed by erosion
        let dilated = this.dilate(binary, width, height, kernelSize);
        let closed = this.erode(dilated, width, height, kernelSize);
        return closed;
    }

    dilate(binary, width, height, kernelSize) {
        const result = new Uint8Array(width * height);
        const radius = Math.floor(kernelSize / 2);

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                let maxVal = binary[idx];

                for (let ky = -radius; ky <= radius; ky++) {
                    for (let kx = -radius; kx <= radius; kx++) {
                        const ny = y + ky;
                        const nx = x + kx;

                        if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                            maxVal = Math.max(maxVal, binary[ny * width + nx]);
                        }
                    }
                }

                result[idx] = maxVal;
            }
        }

        return result;
    }

    erode(binary, width, height, kernelSize) {
        const result = new Uint8Array(width * height);
        const radius = Math.floor(kernelSize / 2);

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                let minVal = binary[idx];

                for (let ky = -radius; ky <= radius; ky++) {
                    for (let kx = -radius; kx <= radius; kx++) {
                        const ny = y + ky;
                        const nx = x + kx;

                        if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                            minVal = Math.min(minVal, binary[ny * width + nx]);
                        }
                    }
                }

                result[idx] = minVal;
            }
        }

        return result;
    }

    /**
     * Edge thinning using Zhang-Suen algorithm
     */
    edgeThinning(binary, width, height, iterations = 1) {
        let thinned = new Uint8Array(binary);

        for (let iter = 0; iter < iterations; iter++) {
            thinned = this.zhangSuenIteration(thinned, width, height);
        }

        return thinned;
    }

    zhangSuenIteration(binary, width, height) {
        const result = new Uint8Array(binary);
        const toRemove = [];

        // Two sub-iterations
        for (let subIter = 0; subIter < 2; subIter++) {
            toRemove.length = 0;

            for (let y = 1; y < height - 1; y++) {
                for (let x = 1; x < width - 1; x++) {
                    const idx = y * width + x;
                    if (result[idx] === 0) continue;

                    // Get 8 neighbors (clockwise from top)
                    const p2 = result[(y - 1) * width + x] > 0 ? 1 : 0;
                    const p3 = result[(y - 1) * width + (x + 1)] > 0 ? 1 : 0;
                    const p4 = result[y * width + (x + 1)] > 0 ? 1 : 0;
                    const p5 = result[(y + 1) * width + (x + 1)] > 0 ? 1 : 0;
                    const p6 = result[(y + 1) * width + x] > 0 ? 1 : 0;
                    const p7 = result[(y + 1) * width + (x - 1)] > 0 ? 1 : 0;
                    const p8 = result[y * width + (x - 1)] > 0 ? 1 : 0;
                    const p9 = result[(y - 1) * width + (x - 1)] > 0 ? 1 : 0;

                    const neighbors = [p2, p3, p4, p5, p6, p7, p8, p9];

                    // Condition 1: 2 <= B(P1) <= 6
                    const blackNeighbors = neighbors.reduce((a, b) => a + b, 0);
                    if (blackNeighbors < 2 || blackNeighbors > 6) continue;

                    // Condition 2: A(P1) = 1
                    let transitions = 0;
                    for (let i = 0; i < 8; i++) {
                        if (neighbors[i] === 0 && neighbors[(i + 1) % 8] === 1) {
                            transitions++;
                        }
                    }
                    if (transitions !== 1) continue;

                    // Condition 3 & 4 (different for each sub-iteration)
                    if (subIter === 0) {
                        if (p2 * p4 * p6 !== 0) continue;
                        if (p4 * p6 * p8 !== 0) continue;
                    } else {
                        if (p2 * p4 * p8 !== 0) continue;
                        if (p2 * p6 * p8 !== 0) continue;
                    }

                    toRemove.push(idx);
                }
            }

            // Remove marked pixels
            for (let idx of toRemove) {
                result[idx] = 0;
            }
        }

        return result;
    }

    /**
     * Create ImageData from binary edge map
     */
    createImageData(binary, width, height) {
        const imageData = new ImageData(width, height);
        const data = imageData.data;

        for (let i = 0; i < binary.length; i++) {
            const val = 255 - binary[i]; // Invert: black lines on white
            data[i * 4] = val;
            data[i * 4 + 1] = val;
            data[i * 4 + 2] = val;
            data[i * 4 + 3] = 255;
        }

        return imageData;
    }
}
