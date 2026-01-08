// Visualization modes: Original, Paint-by-Numbers, Line Drawing

class Visualizer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.mode = 'original';
        this.imageProcessor = null;
        this.colorManager = null;
        this.quantizedData = null;
        this.parameters = {
            numberSize: 16,
            lineWidth: 2,
            detailLevel: 5,
            minRegionSize: 50
        };
    }

    setImageProcessor(processor) {
        this.imageProcessor = processor;
    }

    setColorManager(manager) {
        this.colorManager = manager;
    }

    setMode(mode) {
        this.mode = mode;
    }

    setParameters(params) {
        this.parameters = { ...this.parameters, ...params };
    }

    render() {
        if (!this.imageProcessor || !this.imageProcessor.originalImage) return;

        switch (this.mode) {
            case 'original':
                this.renderOriginal();
                break;
            case 'paintByNumbers':
                this.renderPaintByNumbers();
                break;
            case 'lineDrawing':
                this.renderLineDrawing();
                break;
        }
    }

    renderOriginal() {
        const img = this.imageProcessor.originalImage;
        this.canvas.width = img.width;
        this.canvas.height = img.height;
        this.ctx.drawImage(img, 0, 0);
    }

    renderPaintByNumbers() {
        if (!this.colorManager || this.colorManager.getColorCount() === 0) {
            this.renderOriginal();
            return;
        }

        const colors = this.colorManager.getColors();
        const result = this.imageProcessor.quantizeImage(colors);

        if (!result) return;

        this.quantizedData = result;
        const { canvas: quantizedCanvas, colorMap } = result;

        this.canvas.width = quantizedCanvas.width;
        this.canvas.height = quantizedCanvas.height;

        // Draw quantized image
        this.ctx.drawImage(quantizedCanvas, 0, 0);

        // Apply preview dimming if active
        if (this.colorManager.isPreviewActive()) {
            this.applyPreviewEffect(colorMap);
        }

        // Draw contours
        this.drawContours(colorMap, colors);

        // Draw numbers
        this.drawNumbers(colorMap, colors);
    }

    applyPreviewEffect(colorMap) {
        const previewIndex = this.colorManager.getPreviewColorIndex();
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;

        for (let i = 0; i < colorMap.length; i++) {
            if (colorMap[i] !== previewIndex) {
                const idx = i * 4;
                // Dim non-preview colors
                data[idx] = data[idx] * 0.3;
                data[idx + 1] = data[idx + 1] * 0.3;
                data[idx + 2] = data[idx + 2] * 0.3;
            }
        }

        this.ctx.putImageData(imageData, 0, 0);
    }

    drawContours(colorMap, colors) {
        const width = this.canvas.width;
        const height = this.canvas.height;

        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = this.parameters.lineWidth;

        // Draw borders between different colored regions
        for (let y = 0; y < height - 1; y++) {
            for (let x = 0; x < width - 1; x++) {
                const idx = y * width + x;
                const currentColor = colorMap[idx];

                // Check right neighbor
                const rightColor = colorMap[idx + 1];
                if (currentColor !== rightColor) {
                    this.ctx.beginPath();
                    this.ctx.moveTo(x + 1, y);
                    this.ctx.lineTo(x + 1, y + 1);
                    this.ctx.stroke();
                }

                // Check bottom neighbor
                const bottomColor = colorMap[idx + width];
                if (currentColor !== bottomColor) {
                    this.ctx.beginPath();
                    this.ctx.moveTo(x, y + 1);
                    this.ctx.lineTo(x + 1, y + 1);
                    this.ctx.stroke();
                }
            }
        }
    }

    drawNumbers(colorMap, colors) {
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Find regions and their centers using improved algorithm
        const regions = this.findRegions(colorMap, width, height);

        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';

        for (let region of regions) {
            if (region.size < this.parameters.minRegionSize) continue;

            const color = colors[region.colorIndex];
            if (!color) continue;

            // Find best center point (furthest from edges)
            const centerPoint = this.findOptimalCenter(region, colorMap, width, height);

            // Calculate font size based on region size
            const fontSize = Math.max(8, Math.min(this.parameters.numberSize, Math.sqrt(region.size) * 0.5));
            this.ctx.font = `bold ${fontSize}px Arial`;

            // Use contrasting color for text
            this.ctx.fillStyle = getContrastColor(color.hex);

            // Draw number at optimal center
            this.ctx.fillText(color.number.toString(), centerPoint.x, centerPoint.y);
        }
    }

    findOptimalCenter(region, colorMap, width, height) {
        // If region is small, use geometric center
        if (region.size < 100) {
            return { x: region.centerX, y: region.centerY };
        }

        // For larger regions, find point furthest from edges (distance transform approximation)
        const pixels = [];

        // Collect all pixels in this region
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                if (colorMap[idx] === region.colorIndex) {
                    pixels.push({ x, y });
                }
            }
        }

        // Sample a subset if too many pixels (performance)
        const samplePixels = pixels.length > 500 ?
            pixels.filter((_, i) => i % Math.ceil(pixels.length / 500) === 0) :
            pixels;

        let bestPixel = { x: region.centerX, y: region.centerY };
        let maxMinDist = 0;

        // Find pixel with maximum minimum distance to edges
        for (let pixel of samplePixels) {
            let minDistToEdge = Infinity;

            // Check 8 directions for edge distance
            const directions = [
                { dx: 1, dy: 0 }, { dx: -1, dy: 0 },
                { dx: 0, dy: 1 }, { dx: 0, dy: -1 },
                { dx: 1, dy: 1 }, { dx: -1, dy: -1 },
                { dx: 1, dy: -1 }, { dx: -1, dy: 1 }
            ];

            for (let dir of directions) {
                let dist = 0;
                let cx = pixel.x;
                let cy = pixel.y;

                // Ray cast until we hit a different color
                while (cx >= 0 && cx < width && cy >= 0 && cy < height) {
                    const idx = cy * width + cx;
                    if (colorMap[idx] !== region.colorIndex) break;

                    cx += dir.dx;
                    cy += dir.dy;
                    dist++;
                }

                minDistToEdge = Math.min(minDistToEdge, dist);
            }

            if (minDistToEdge > maxMinDist) {
                maxMinDist = minDistToEdge;
                bestPixel = pixel;
            }
        }

        return bestPixel;
    }

    findRegions(colorMap, width, height) {
        const visited = new Uint8Array(width * height);
        const regions = [];

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                if (visited[idx]) continue;

                const colorIndex = colorMap[idx];
                const region = this.floodFill(colorMap, visited, x, y, width, height, colorIndex);

                if (region.size > 0) {
                    regions.push(region);
                }
            }
        }

        return regions;
    }

    floodFill(colorMap, visited, startX, startY, width, height, targetColor) {
        const stack = [{ x: startX, y: startY }];
        const region = {
            colorIndex: targetColor,
            size: 0,
            centerX: 0,
            centerY: 0,
            sumX: 0,
            sumY: 0
        };

        while (stack.length > 0) {
            const { x, y } = stack.pop();

            if (x < 0 || x >= width || y < 0 || y >= height) continue;

            const idx = y * width + x;

            if (visited[idx] || colorMap[idx] !== targetColor) continue;

            visited[idx] = 1;
            region.size++;
            region.sumX += x;
            region.sumY += y;

            // Add neighbors
            stack.push({ x: x + 1, y });
            stack.push({ x: x - 1, y });
            stack.push({ x, y: y + 1 });
            stack.push({ x, y: y - 1 });
        }

        if (region.size > 0) {
            region.centerX = Math.round(region.sumX / region.size);
            region.centerY = Math.round(region.sumY / region.size);
        }

        return region;
    }

    renderLineDrawing() {
        // ALWAYS use quantized version if colors are detected (removes noise/JPG artifacts)
        if (this.colorManager && this.colorManager.getColorCount() > 0) {
            // First ensure we have quantized data
            if (!this.quantizedData) {
                const colors = this.colorManager.getColors();
                this.quantizedData = this.imageProcessor.quantizeImage(colors);
            }

            if (this.quantizedData) {
                const { colorMap } = this.quantizedData;

                // Use quantized color map for crystal clear edges
                const edgeCanvas = this.imageProcessor.detectEdges(
                    this.parameters.detailLevel,
                    true,  // Always use quantized
                    colorMap
                );

                if (edgeCanvas) {
                    this.canvas.width = edgeCanvas.width;
                    this.canvas.height = edgeCanvas.height;
                    this.ctx.drawImage(edgeCanvas, 0, 0);
                    this.applyLineDilation();
                    return;
                }
            }
        }

        // Fallback to original if no colors detected
        const edgeCanvas = this.imageProcessor.detectEdges(
            this.parameters.detailLevel,
            false,
            null
        );

        if (!edgeCanvas) {
            this.renderOriginal();
            return;
        }

        this.canvas.width = edgeCanvas.width;
        this.canvas.height = edgeCanvas.height;
        this.ctx.drawImage(edgeCanvas, 0, 0);
        this.applyLineDilation();
    }

    applyLineDilation() {
        // Apply line width if needed (dilation for thicker lines)
        if (this.parameters.lineWidth > 1) {
            const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            const originalData = new Uint8ClampedArray(imageData.data);
            const lineWidth = Math.floor(this.parameters.lineWidth / 2);

            for (let y = 0; y < this.canvas.height; y++) {
                for (let x = 0; x < this.canvas.width; x++) {
                    const idx = (y * this.canvas.width + x) * 4;

                    // If this pixel is black (edge)
                    if (originalData[idx] < 128) {
                        // Dilate by drawing circle
                        for (let dy = -lineWidth; dy <= lineWidth; dy++) {
                            for (let dx = -lineWidth; dx <= lineWidth; dx++) {
                                // Only within circle
                                if (dx * dx + dy * dy <= lineWidth * lineWidth) {
                                    const ny = y + dy;
                                    const nx = x + dx;

                                    if (nx >= 0 && nx < this.canvas.width && ny >= 0 && ny < this.canvas.height) {
                                        const nidx = (ny * this.canvas.width + nx) * 4;
                                        imageData.data[nidx] = 0;
                                        imageData.data[nidx + 1] = 0;
                                        imageData.data[nidx + 2] = 0;
                                        imageData.data[nidx + 3] = 255;
                                    }
                                }
                            }
                        }
                    }
                }
            }

            this.ctx.putImageData(imageData, 0, 0);
        }
    }

    getCanvas() {
        return this.canvas;
    }

    exportSVG() {
        if (this.mode !== 'paintByNumbers' || !this.quantizedData) {
            alert('SVG export is alleen beschikbaar in Paint-by-Numbers mode');
            return null;
        }

        const { colorMap } = this.quantizedData;
        const colors = this.colorManager.getColors();
        const width = this.canvas.width;
        const height = this.canvas.height;

        let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">
<rect width="${width}" height="${height}" fill="white"/>
`;

        // Group pixels by color
        const colorGroups = {};
        for (let i = 0; i < colorMap.length; i++) {
            const colorIndex = colorMap[i];
            if (!colorGroups[colorIndex]) {
                colorGroups[colorIndex] = [];
            }
            colorGroups[colorIndex].push(i);
        }

        // Draw each color group
        for (let colorIndex in colorGroups) {
            const color = colors[colorIndex];
            if (!color) continue;

            svg += `<g fill="${color.hex}">\n`;

            for (let pixelIdx of colorGroups[colorIndex]) {
                const x = pixelIdx % width;
                const y = Math.floor(pixelIdx / width);
                svg += `  <rect x="${x}" y="${y}" width="1" height="1"/>\n`;
            }

            svg += `</g>\n`;
        }

        svg += `</svg>`;
        return svg;
    }
}
