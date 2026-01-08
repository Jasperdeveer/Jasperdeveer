// Main application controller

class PaintByNumbersApp {
    constructor() {
        // Initialize components
        this.imageProcessor = new ImageProcessor();
        this.colorManager = new ColorManager();
        this.visualizer = new Visualizer(document.getElementById('mainCanvas'));
        this.legend = new Legend(
            document.getElementById('legend'),
            document.getElementById('sprayResults')
        );

        // Connect components
        this.visualizer.setImageProcessor(this.imageProcessor);
        this.visualizer.setColorManager(this.colorManager);

        // State
        this.currentMode = 'original';
        this.zoomLevel = 1;
        this.regionStats = null;

        // Initialize UI
        this.initializeEventListeners();
        this.updateUI();
    }

    initializeEventListeners() {
        // Image upload
        document.getElementById('imageUpload').addEventListener('change', (e) => {
            this.handleImageUpload(e.target.files[0]);
        });

        // Mode buttons
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setMode(e.target.dataset.mode);
            });
        });

        // Color detection
        document.getElementById('detectColors').addEventListener('click', () => {
            this.detectColors();
        });

        // Undo
        document.getElementById('undoBtn').addEventListener('click', () => {
            this.undo();
        });

        // Parameter controls
        this.setupParameterControl('colorCount', (value) => {
            document.getElementById('colorCountValue').textContent = value;
        });

        this.setupParameterControl('numberSize', (value) => {
            document.getElementById('numberSizeValue').textContent = value === '16' ? 'Auto' : value;
            this.visualizer.setParameters({ numberSize: parseInt(value) });
            this.render();
        });

        this.setupParameterControl('lineWidth', (value) => {
            document.getElementById('lineWidthValue').textContent = value;
            this.visualizer.setParameters({ lineWidth: parseInt(value) });
            this.render();
        });

        this.setupParameterControl('detailLevel', (value) => {
            document.getElementById('detailLevelValue').textContent = value;
            this.visualizer.setParameters({ detailLevel: parseInt(value) });
            this.render();
        });

        this.setupParameterControl('minRegionSize', (value) => {
            document.getElementById('minRegionSizeValue').textContent = value;
            this.visualizer.setParameters({ minRegionSize: parseInt(value) });
            this.render();
        });

        // Canvas dimensions
        document.getElementById('canvasWidth').addEventListener('input', debounce((e) => {
            const value = parseInt(e.target.value);
            document.getElementById('canvasWidthValue').textContent = value;
            this.legend.updateDimensions(
                value,
                parseInt(document.getElementById('canvasHeight').value)
            );
            this.updateLegend();
        }, 500));

        document.getElementById('canvasHeight').addEventListener('input', debounce((e) => {
            const value = parseInt(e.target.value);
            document.getElementById('canvasHeightValue').textContent = value;
            this.legend.updateDimensions(
                parseInt(document.getElementById('canvasWidth').value),
                value
            );
            this.updateLegend();
        }, 500));

        // Zoom controls
        document.getElementById('zoomIn').addEventListener('click', () => {
            this.zoom(0.1);
        });

        document.getElementById('zoomOut').addEventListener('click', () => {
            this.zoom(-0.1);
        });

        document.getElementById('zoomReset').addEventListener('click', () => {
            this.resetZoom();
        });

        // Export
        document.getElementById('exportSVG').addEventListener('click', () => {
            this.exportSVG();
        });

        document.getElementById('exportPNG').addEventListener('click', () => {
            this.exportPNG();
        });
    }

    setupParameterControl(id, callback) {
        const element = document.getElementById(id);
        element.addEventListener('input', debounce((e) => {
            callback(e.target.value);
        }, 300));
    }

    async handleImageUpload(file) {
        if (!file) return;

        showLoading('Afbeelding laden...');

        try {
            updateLoadingStep('Afbeelding inlezen...');
            const img = await this.imageProcessor.loadImage(file);

            // Show preview
            const preview = document.getElementById('imagePreview');
            preview.innerHTML = `<img src="${img.src}" alt="Preview">`;

            // Auto-detect colors
            await this.detectColors();
        } catch (error) {
            console.error('Error loading image:', error);
            hideLoading();
            alert('Fout bij het laden van de afbeelding');
        }
    }

    async detectColors() {
        showLoading('Kleuren analyseren...');

        try {
            const numColors = parseInt(document.getElementById('colorCount').value);

            updateLoadingStep(`K-means clustering voor ${numColors} kleuren...`);

            // Use setTimeout to allow UI to update
            await new Promise(resolve => setTimeout(resolve, 50));

            const colors = this.imageProcessor.detectColors(numColors);

            if (colors.length > 0) {
                updateLoadingStep('Kleurenpalet opslaan...');
                this.colorManager.setColors(colors);
                this.updateColorPalette();

                updateLoadingStep('Visualisatie genereren...');
                await this.render();
            }
        } finally {
            hideLoading();
        }
    }

    async setMode(mode) {
        this.currentMode = mode;
        this.visualizer.setMode(mode);

        // Update active button
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-mode="${mode}"]`).classList.add('active');

        await this.render();
    }

    async render() {
        showLoading('Visualisatie genereren...');

        try {
            // Update step based on mode
            if (this.currentMode === 'paintByNumbers') {
                updateLoadingStep('Afbeelding quantiseren naar kleurenpalet...');
                await new Promise(resolve => setTimeout(resolve, 50));

                this.visualizer.render();

                updateLoadingStep('Contouren tekenen...');
                await new Promise(resolve => setTimeout(resolve, 50));

                updateLoadingStep('Nummers plaatsen in kleurvlakken...');
                await new Promise(resolve => setTimeout(resolve, 50));

            } else if (this.currentMode === 'lineDrawing') {
                updateLoadingStep('Afbeelding quantiseren...');
                await new Promise(resolve => setTimeout(resolve, 50));

                updateLoadingStep('Canny edge detection uitvoeren...');
                await new Promise(resolve => setTimeout(resolve, 50));

                this.visualizer.render();

                updateLoadingStep('Lijnen verfijnen...');
                await new Promise(resolve => setTimeout(resolve, 50));

            } else {
                this.visualizer.render();
            }

            // Calculate region stats for paint-by-numbers mode
            if (this.currentMode === 'paintByNumbers' && this.visualizer.quantizedData) {
                updateLoadingStep('Statistieken berekenen...');
                const { colorMap } = this.visualizer.quantizedData;
                this.regionStats = this.imageProcessor.calculateRegionStats(
                    colorMap,
                    this.colorManager.getColors()
                );
            }

            updateLoadingStep('Legenda updaten...');
            this.updateLegend();
        } finally {
            hideLoading();
        }
    }

    updateColorPalette() {
        const colors = this.colorManager.getColors();
        const palette = document.getElementById('colorPalette');

        if (colors.length === 0) {
            palette.innerHTML = '<p style="color: #999;">Geen kleuren geselecteerd</p>';
            return;
        }

        let html = '';

        colors.forEach((color, index) => {
            const isDimmed = this.colorManager.isPreviewActive() &&
                this.colorManager.getPreviewColorIndex() !== index;

            html += `
                <div class="color-item ${isDimmed ? 'dimmed' : ''}" data-color-id="${color.id}">
                    <div class="color-number">${color.number}</div>
                    <div class="color-swatch" style="background-color: ${color.hex}"
                         data-color-index="${index}"></div>
                    <input type="text" class="color-name" value="${color.name}"
                           data-color-id="${color.id}">
                    <div class="color-actions">
                        <button class="preview-btn" data-color-index="${index}">👁</button>
                        <button class="remove-btn" data-color-id="${color.id}">✕</button>
                    </div>
                </div>
            `;
        });

        palette.innerHTML = html;

        // Add event listeners
        palette.querySelectorAll('.color-name').forEach(input => {
            input.addEventListener('change', (e) => {
                const colorId = parseInt(e.target.dataset.colorId);
                this.colorManager.renameColor(colorId, e.target.value);
                this.updateLegend();
            });
        });

        palette.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const colorId = parseInt(e.target.dataset.colorId);
                this.colorManager.removeColor(colorId);
                this.updateColorPalette();
                this.render();
            });
        });

        palette.querySelectorAll('.preview-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const colorIndex = parseInt(e.target.dataset.colorIndex);
                this.togglePreview(colorIndex);
            });
        });

        palette.querySelectorAll('.color-swatch').forEach(swatch => {
            swatch.addEventListener('click', (e) => {
                const colorIndex = parseInt(e.target.dataset.colorIndex);
                this.showColorPicker(colorIndex);
            });
        });
    }

    togglePreview(colorIndex) {
        if (this.colorManager.getPreviewColorIndex() === colorIndex) {
            this.colorManager.clearPreview();
        } else {
            this.colorManager.setPreviewColor(colorIndex);
        }

        this.updateColorPalette();
        this.render();
    }

    showColorPicker(colorIndex) {
        const color = this.colorManager.getColorByIndex(colorIndex);
        if (!color) return;

        const newColor = prompt(`Nieuwe kleur voor ${color.name} (HEX):`, color.hex);
        if (!newColor) return;

        const rgb = hexToRgb(newColor);
        if (rgb) {
            this.colorManager.updateColor(color.id, {
                r: rgb.r,
                g: rgb.g,
                b: rgb.b,
                hex: newColor
            });
            this.updateColorPalette();
            this.render();
        }
    }

    undo() {
        if (this.colorManager.undo()) {
            this.updateColorPalette();
            this.render();
        }
    }

    updateLegend() {
        this.legend.render(this.colorManager.getColors(), this.regionStats);
    }

    updateUI() {
        // Update undo button
        document.getElementById('undoBtn').disabled = !this.colorManager.canUndo();
    }

    zoom(delta) {
        this.zoomLevel = Math.max(0.1, Math.min(5, this.zoomLevel + delta));
        this.applyZoom();
    }

    resetZoom() {
        this.zoomLevel = 1;
        this.applyZoom();
    }

    applyZoom() {
        const canvas = this.visualizer.getCanvas();
        canvas.style.transform = `scale(${this.zoomLevel})`;
        canvas.style.transformOrigin = 'top left';
        document.getElementById('zoomLevel').textContent = `${Math.round(this.zoomLevel * 100)}%`;
    }

    async exportSVG() {
        showLoading('SVG exporteren...');
        try {
            updateLoadingStep('SVG genereren...');
            await new Promise(resolve => setTimeout(resolve, 50));

            const svg = this.visualizer.exportSVG();
            if (svg) {
                updateLoadingStep('Bestand downloaden...');
                downloadFile(svg, 'paint-by-numbers.svg', 'image/svg+xml');
            }
        } finally {
            hideLoading();
        }
    }

    async exportPNG() {
        showLoading('PNG exporteren...');
        try {
            updateLoadingStep('Afbeelding converteren...');
            await new Promise(resolve => setTimeout(resolve, 50));

            const canvas = this.visualizer.getCanvas();
            canvas.toBlob((blob) => {
                updateLoadingStep('Bestand downloaden...');
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'paint-by-numbers.png';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
                hideLoading();
            });
        } catch (error) {
            hideLoading();
            throw error;
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new PaintByNumbersApp();

    // Make app globally accessible for debugging
    window.app = app;
});
