// Image processing and color detection

class ImageProcessor {
    constructor() {
        this.originalImage = null;
        this.imageData = null;
        this.width = 0;
        this.height = 0;
        this.aiEdgeDetector = new AIEdgeDetector();
    }

    loadImage(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    this.originalImage = img;
                    this.extractImageData(img);
                    resolve(img);
                };
                img.onerror = reject;
                img.src = e.target.result;
            };
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    extractImageData(img) {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);

        this.imageData = ctx.getImageData(0, 0, img.width, img.height);
        this.width = img.width;
        this.height = img.height;
    }

    // K-means clustering for color detection
    detectColors(numColors, maxIterations = 30) {
        if (!this.imageData) return [];

        // Sample pixels (use every nth pixel for performance)
        const pixels = [];
        const data = this.imageData.data;
        const sampleRate = Math.max(1, Math.floor(this.width * this.height / 10000));

        for (let i = 0; i < data.length; i += 4 * sampleRate) {
            pixels.push({
                r: data[i],
                g: data[i + 1],
                b: data[i + 2]
            });
        }

        // Initialize centroids randomly
        let centroids = [];
        for (let i = 0; i < numColors; i++) {
            const randomPixel = pixels[Math.floor(Math.random() * pixels.length)];
            centroids.push({ ...randomPixel });
        }

        // K-means iterations
        for (let iter = 0; iter < maxIterations; iter++) {
            // Assign pixels to nearest centroid
            const clusters = Array(numColors).fill(null).map(() => []);

            for (let pixel of pixels) {
                let minDist = Infinity;
                let clusterIndex = 0;

                for (let i = 0; i < centroids.length; i++) {
                    const dist = colorDistance(pixel, centroids[i]);
                    if (dist < minDist) {
                        minDist = dist;
                        clusterIndex = i;
                    }
                }

                clusters[clusterIndex].push(pixel);
            }

            // Recalculate centroids
            let changed = false;
            for (let i = 0; i < centroids.length; i++) {
                if (clusters[i].length === 0) continue;

                const newCentroid = {
                    r: 0,
                    g: 0,
                    b: 0
                };

                for (let pixel of clusters[i]) {
                    newCentroid.r += pixel.r;
                    newCentroid.g += pixel.g;
                    newCentroid.b += pixel.b;
                }

                newCentroid.r = Math.round(newCentroid.r / clusters[i].length);
                newCentroid.g = Math.round(newCentroid.g / clusters[i].length);
                newCentroid.b = Math.round(newCentroid.b / clusters[i].length);

                if (colorDistance(newCentroid, centroids[i]) > 1) {
                    changed = true;
                }

                centroids[i] = newCentroid;
            }

            if (!changed) break;
        }

        // Convert to color objects
        const rawColors = centroids.map((c, index) => ({
            id: Date.now() + index,
            r: c.r,
            g: c.g,
            b: c.b,
            hex: rgbToHex(c.r, c.g, c.b)
        }));

        // Post-process: merge similar colors and add intelligent names
        const processed = processDetectedColors(rawColors, 30, 'brightness');

        // Add unique IDs and return
        return processed.map((c, index) => ({
            id: Date.now() + index,
            r: c.r,
            g: c.g,
            b: c.b,
            hex: c.hex,
            name: c.name
        }));
    }

    // Quantize image to specific colors
    quantizeImage(colors) {
        if (!this.imageData) return null;

        const canvas = document.createElement('canvas');
        canvas.width = this.width;
        canvas.height = this.height;
        const ctx = canvas.getContext('2d');

        const newImageData = ctx.createImageData(this.width, this.height);
        const data = this.imageData.data;
        const newData = newImageData.data;

        // Map to store which color index each pixel belongs to
        const colorMap = new Uint8Array(this.width * this.height);

        for (let i = 0; i < data.length; i += 4) {
            const pixel = {
                r: data[i],
                g: data[i + 1],
                b: data[i + 2]
            };

            // Find nearest color
            let minDist = Infinity;
            let nearestColor = colors[0];
            let colorIndex = 0;

            for (let j = 0; j < colors.length; j++) {
                const dist = colorDistance(pixel, colors[j]);
                if (dist < minDist) {
                    minDist = dist;
                    nearestColor = colors[j];
                    colorIndex = j;
                }
            }

            // Store color index
            const pixelIndex = i / 4;
            colorMap[pixelIndex] = colorIndex;

            // Set new color
            newData[i] = nearestColor.r;
            newData[i + 1] = nearestColor.g;
            newData[i + 2] = nearestColor.b;
            newData[i + 3] = 255;
        }

        ctx.putImageData(newImageData, 0, 0);

        // Smooth regions to eliminate noise
        const smoothedColorMap = this.smoothRegions(colorMap, this.width, this.height);

        return { canvas, colorMap: smoothedColorMap };
    }

    // Smooth regions by merging small regions with their largest neighbor
    smoothRegions(colorMap, width, height, minSize = 100) {
        const result = new Uint8Array(colorMap);
        let changed = true;
        let iterations = 0;
        const maxIterations = 10;

        while (changed && iterations < maxIterations) {
            changed = false;
            iterations++;

            // Find all regions
            const visited = new Uint8Array(width * height);
            const regions = [];

            for (let y = 0; y < height; y++) {
                for (let x = 0; x < width; x++) {
                    const idx = y * width + x;
                    if (visited[idx]) continue;

                    const colorIndex = result[idx];
                    const region = this.floodFillRegion(result, visited, x, y, width, height, colorIndex);

                    if (region.pixels.length > 0) {
                        regions.push({
                            colorIndex,
                            size: region.pixels.length,
                            pixels: region.pixels,
                            neighbors: new Set()
                        });
                    }
                }
            }

            // For each small region, find its neighbors
            for (let region of regions) {
                if (region.size >= minSize) continue;

                // Find all neighboring colors
                for (let pixelIdx of region.pixels) {
                    const x = pixelIdx % width;
                    const y = Math.floor(pixelIdx / width);

                    // Check 4 neighbors
                    const neighbors = [
                        [x - 1, y], [x + 1, y],
                        [x, y - 1], [x, y + 1]
                    ];

                    for (let [nx, ny] of neighbors) {
                        if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;
                        const nIdx = ny * width + nx;
                        const neighborColor = result[nIdx];
                        if (neighborColor !== region.colorIndex) {
                            region.neighbors.add(neighborColor);
                        }
                    }
                }

                // Find the largest neighboring region
                if (region.neighbors.size > 0) {
                    let largestNeighborSize = 0;
                    let largestNeighborColor = null;

                    for (let neighborColor of region.neighbors) {
                        const neighborRegion = regions.find(r => r.colorIndex === neighborColor);
                        if (neighborRegion && neighborRegion.size > largestNeighborSize) {
                            largestNeighborSize = neighborRegion.size;
                            largestNeighborColor = neighborColor;
                        }
                    }

                    // Merge this region with largest neighbor
                    if (largestNeighborColor !== null) {
                        for (let pixelIdx of region.pixels) {
                            result[pixelIdx] = largestNeighborColor;
                        }
                        changed = true;
                    }
                }
            }
        }

        return result;
    }

    floodFillRegion(colorMap, visited, startX, startY, width, height, targetColor) {
        const pixels = [];
        const stack = [[startX, startY]];

        while (stack.length > 0) {
            const [x, y] = stack.pop();
            if (x < 0 || x >= width || y < 0 || y >= height) continue;

            const idx = y * width + x;
            if (visited[idx]) continue;
            if (colorMap[idx] !== targetColor) continue;

            visited[idx] = 1;
            pixels.push(idx);

            // Add 4-connected neighbors
            stack.push([x + 1, y]);
            stack.push([x - 1, y]);
            stack.push([x, y + 1]);
            stack.push([x, y - 1]);
        }

        return { pixels };
    }

    // Gaussian blur for noise reduction
    applyGaussianBlur(gray, width, height, sigma = 1.4) {
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

    // Detect edges with AI-enhanced Canny algorithm for crisp coloring book lines
    detectEdges(detailLevel = 5, useQuantized = false, colorMap = null) {
        if (!this.imageData) return null;

        const canvas = document.createElement('canvas');
        canvas.width = this.width;
        canvas.height = this.height;
        const ctx = canvas.getContext('2d');

        // Setup progress callback if available
        if (typeof updateProgress === 'function') {
            this.aiEdgeDetector.setProgressCallback((percent, message) => {
                updateProgress(percent, message);
            });
        }

        // Use AI-powered edge detection for superior results
        const edgeImageData = this.aiEdgeDetector.detectEdgesAdvanced(
            this.imageData,
            this.width,
            this.height,
            {
                detailLevel: detailLevel,
                useBilateralFilter: true,
                useAdaptiveThreshold: true,
                useNonMaxSuppression: true,
                useHysteresis: true,
                useMultiScale: true,      // Enable multi-scale for detail preservation
                preserveCorners: true     // Enable corner detection
            }
        );

        ctx.putImageData(edgeImageData, 0, 0);
        return canvas;
    }

    // Calculate region statistics for each color
    calculateRegionStats(colorMap, colors) {
        const stats = colors.map(() => ({
            pixelCount: 0,
            regions: []
        }));

        // Count pixels per color
        for (let i = 0; i < colorMap.length; i++) {
            const colorIndex = colorMap[i];
            stats[colorIndex].pixelCount++;
        }

        // Calculate area in cm² based on canvas dimensions
        const totalPixels = this.width * this.height;

        return stats.map((stat, index) => ({
            colorIndex: index,
            pixelCount: stat.pixelCount,
            percentage: (stat.pixelCount / totalPixels * 100).toFixed(2)
        }));
    }
}
