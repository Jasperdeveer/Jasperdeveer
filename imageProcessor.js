// Image processing and color detection

class ImageProcessor {
    constructor() {
        this.originalImage = null;
        this.imageData = null;
        this.width = 0;
        this.height = 0;
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

        // Convert to color objects with names
        return centroids.map((c, index) => ({
            id: Date.now() + index,
            r: c.r,
            g: c.g,
            b: c.b,
            hex: rgbToHex(c.r, c.g, c.b),
            name: generateColorName(c.r, c.g, c.b)
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
        return { canvas, colorMap };
    }

    // Detect edges for line drawing mode
    detectEdges(threshold = 30) {
        if (!this.imageData) return null;

        const canvas = document.createElement('canvas');
        canvas.width = this.width;
        canvas.height = this.height;
        const ctx = canvas.getContext('2d');

        // Convert to grayscale first
        const gray = new Uint8Array(this.width * this.height);
        const data = this.imageData.data;

        for (let i = 0; i < data.length; i += 4) {
            const idx = i / 4;
            gray[idx] = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
        }

        // Sobel edge detection
        const edges = new Uint8Array(this.width * this.height);

        for (let y = 1; y < this.height - 1; y++) {
            for (let x = 1; x < this.width - 1; x++) {
                const idx = y * this.width + x;

                // Sobel kernels
                const gx =
                    -1 * gray[(y - 1) * this.width + (x - 1)] +
                    1 * gray[(y - 1) * this.width + (x + 1)] +
                    -2 * gray[y * this.width + (x - 1)] +
                    2 * gray[y * this.width + (x + 1)] +
                    -1 * gray[(y + 1) * this.width + (x - 1)] +
                    1 * gray[(y + 1) * this.width + (x + 1)];

                const gy =
                    -1 * gray[(y - 1) * this.width + (x - 1)] +
                    -2 * gray[(y - 1) * this.width + x] +
                    -1 * gray[(y - 1) * this.width + (x + 1)] +
                    1 * gray[(y + 1) * this.width + (x - 1)] +
                    2 * gray[(y + 1) * this.width + x] +
                    1 * gray[(y + 1) * this.width + (x + 1)];

                const magnitude = Math.sqrt(gx * gx + gy * gy);
                edges[idx] = magnitude > threshold ? 255 : 0;
            }
        }

        // Draw edges
        const imageData = ctx.createImageData(this.width, this.height);
        for (let i = 0; i < edges.length; i++) {
            const val = edges[i];
            imageData.data[i * 4] = val;
            imageData.data[i * 4 + 1] = val;
            imageData.data[i * 4 + 2] = val;
            imageData.data[i * 4 + 3] = 255;
        }

        ctx.putImageData(imageData, 0, 0);
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
