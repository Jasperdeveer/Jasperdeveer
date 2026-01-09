// Presentation Mode for beamer projection workflow
// Features: Canvas-only fullscreen, Zoom/Pan, Grid overlay, Auto-fading keyboard shortcuts

class PresentationMode {
    constructor(canvas, visualizer) {
        this.canvas = canvas;
        this.visualizer = visualizer;
        this.isActive = false;
        this.isPanning = false;
        this.showNumbers = true;
        this.showGrid = false;
        this.gridType = '3x3'; // '2x2', '3x3', '4x4', 'none'

        // Transform state
        this.scale = 1.0;
        this.translateX = 0;
        this.translateY = 0;
        this.panStartX = 0;
        this.panStartY = 0;

        // Mouse activity tracking for shortcuts overlay
        this.mouseActivityTimeout = null;
        this.shortcutsVisible = false;
        this.inactivityDelay = 5000; // 5 seconds

        // UI elements
        this.shortcutsOverlay = null;
        this.fullscreenContainer = null;
        this.gridCanvas = null;
        this.canvasContainer = null;

        // Store original parent for restoration
        this.originalParent = null;
        this.originalCanvasStyle = null;

        this.initialize();
    }

    initialize() {
        // Create fullscreen presentation container
        this.createFullscreenContainer();

        // Create shortcuts overlay
        this.createShortcutsOverlay();

        // Create grid overlay canvas
        this.createGridCanvas();
    }

    createFullscreenContainer() {
        // Create fullscreen container
        this.fullscreenContainer = document.createElement('div');
        this.fullscreenContainer.className = 'presentation-fullscreen-container';
        this.fullscreenContainer.style.display = 'none';

        // Create canvas container inside fullscreen container
        this.canvasContainer = document.createElement('div');
        this.canvasContainer.className = 'presentation-canvas-container';

        this.fullscreenContainer.appendChild(this.canvasContainer);
        document.body.appendChild(this.fullscreenContainer);
    }

    createGridCanvas() {
        this.gridCanvas = document.createElement('canvas');
        this.gridCanvas.className = 'presentation-grid-overlay';
        this.gridCanvas.style.display = 'none';
        this.canvasContainer.appendChild(this.gridCanvas);
    }

    createShortcutsOverlay() {
        this.shortcutsOverlay = document.createElement('div');
        this.shortcutsOverlay.className = 'keyboard-shortcuts-overlay';
        this.shortcutsOverlay.innerHTML = `
            <div class="shortcuts-content">
                <h3>⌨️ Sneltoetsen</h3>
                <div class="shortcuts-grid">
                    <div class="shortcut-item">
                        <kbd>ESC</kbd>
                        <span>Exit presentatie</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>+</kbd> / <kbd>-</kbd>
                        <span>Zoom in/uit</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>0</kbd>
                        <span>Reset zoom</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Sleep</kbd>
                        <span>Pan canvas</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>N</kbd>
                        <span>Toggle nummers</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>G</kbd>
                        <span>Toggle grid</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>1-4</kbd>
                        <span>Grid type (2x2 tot 4x4)</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>←</kbd> <kbd>→</kbd> <kbd>↑</kbd> <kbd>↓</kbd>
                        <span>Pan met pijltjes</span>
                    </div>
                </div>
            </div>
        `;

        this.fullscreenContainer.appendChild(this.shortcutsOverlay);
    }

    activate() {
        if (this.isActive) return;

        // Store original parent and styles
        this.originalParent = this.canvas.parentElement;
        this.originalCanvasStyle = {
            transform: this.canvas.style.transform,
            transformOrigin: this.canvas.style.transformOrigin,
            maxWidth: this.canvas.style.maxWidth,
            maxHeight: this.canvas.style.maxHeight
        };

        // Move canvas to presentation container
        this.canvasContainer.insertBefore(this.canvas, this.gridCanvas);

        // Show fullscreen container
        this.fullscreenContainer.style.display = 'flex';

        // Reset canvas styles for fullscreen
        this.canvas.style.maxWidth = '100%';
        this.canvas.style.maxHeight = '100%';

        // Update grid canvas size
        this.updateGridCanvas();

        // Reset transform
        this.scale = 1.0;
        this.translateX = 0;
        this.translateY = 0;
        this.applyTransform();

        // Add event listeners
        this.addEventListeners();

        // Show shortcuts initially
        this.showShortcuts();
        this.resetInactivityTimer();

        this.isActive = true;
    }

    deactivate() {
        if (!this.isActive) return;

        // Remove event listeners
        this.removeEventListeners();

        // Restore canvas to original parent
        if (this.originalParent) {
            this.originalParent.appendChild(this.canvas);
        }

        // Restore original canvas styles
        if (this.originalCanvasStyle) {
            this.canvas.style.transform = this.originalCanvasStyle.transform;
            this.canvas.style.transformOrigin = this.originalCanvasStyle.transformOrigin;
            this.canvas.style.maxWidth = this.originalCanvasStyle.maxWidth;
            this.canvas.style.maxHeight = this.originalCanvasStyle.maxHeight;
        }

        // Hide fullscreen container
        this.fullscreenContainer.style.display = 'none';

        // Clear timeout
        if (this.mouseActivityTimeout) {
            clearTimeout(this.mouseActivityTimeout);
        }

        this.isActive = false;
    }

    addEventListeners() {
        // Store bound functions for removal later
        this.boundMouseMove = (e) => this.onMouseMove(e);
        this.boundKeyDown = (e) => this.onKeyDown(e);
        this.boundMouseDown = (e) => this.onMouseDown(e);
        this.boundMouseDrag = (e) => this.onMouseDrag(e);
        this.boundMouseUp = (e) => this.onMouseUp(e);
        this.boundWheel = (e) => this.onWheel(e);

        document.addEventListener('mousemove', this.boundMouseMove);
        document.addEventListener('keydown', this.boundKeyDown);
        this.canvasContainer.addEventListener('mousedown', this.boundMouseDown);
        document.addEventListener('mousemove', this.boundMouseDrag);
        document.addEventListener('mouseup', this.boundMouseUp);
        this.canvasContainer.addEventListener('wheel', this.boundWheel);
    }

    removeEventListeners() {
        document.removeEventListener('mousemove', this.boundMouseMove);
        document.removeEventListener('keydown', this.boundKeyDown);
        this.canvasContainer.removeEventListener('mousedown', this.boundMouseDown);
        document.removeEventListener('mousemove', this.boundMouseDrag);
        document.removeEventListener('mouseup', this.boundMouseUp);
        this.canvasContainer.removeEventListener('wheel', this.boundWheel);
    }

    onMouseMove(e) {
        if (!this.isActive) return;

        // Show shortcuts overlay
        this.showShortcuts();

        // Reset inactivity timer
        this.resetInactivityTimer();
    }

    showShortcuts() {
        if (!this.shortcutsVisible) {
            this.shortcutsOverlay.classList.add('visible');
            this.shortcutsVisible = true;
        }
    }

    hideShortcuts() {
        if (this.shortcutsVisible) {
            this.shortcutsOverlay.classList.remove('visible');
            this.shortcutsVisible = false;
        }
    }

    resetInactivityTimer() {
        if (this.mouseActivityTimeout) {
            clearTimeout(this.mouseActivityTimeout);
        }

        this.mouseActivityTimeout = setTimeout(() => {
            this.hideShortcuts();
        }, this.inactivityDelay);
    }

    onKeyDown(e) {
        if (!this.isActive) return;

        // ESC - Exit presentation mode
        if (e.key === 'Escape') {
            e.preventDefault();
            this.deactivate();
            return;
        }

        // + or = - Zoom in
        if (e.key === '+' || e.key === '=') {
            e.preventDefault();
            this.zoomIn();
        }

        // - or _ - Zoom out
        if (e.key === '-' || e.key === '_') {
            e.preventDefault();
            this.zoomOut();
        }

        // 0 - Reset zoom
        if (e.key === '0') {
            e.preventDefault();
            this.resetZoom();
        }

        // N - Toggle numbers
        if (e.key === 'n' || e.key === 'N') {
            e.preventDefault();
            this.toggleNumbers();
        }

        // G - Toggle grid
        if (e.key === 'g' || e.key === 'G') {
            e.preventDefault();
            this.toggleGrid();
        }

        // 1-4 - Set grid type
        if (e.key >= '1' && e.key <= '4') {
            e.preventDefault();
            const gridSize = parseInt(e.key) + 1; // 1 -> 2x2, 2 -> 3x3, etc.
            this.setGridType(`${gridSize}x${gridSize}`);
        }

        // Arrow keys - Pan
        if (e.key.startsWith('Arrow')) {
            e.preventDefault();
            this.panWithArrows(e.key);
        }
    }

    onMouseDown(e) {
        if (!this.isActive) return;

        if (e.button === 0) { // Left click
            this.isPanning = true;
            this.panStartX = e.clientX - this.translateX;
            this.panStartY = e.clientY - this.translateY;
            this.canvasContainer.style.cursor = 'grabbing';
        }
    }

    onMouseDrag(e) {
        if (!this.isActive || !this.isPanning) return;

        this.translateX = e.clientX - this.panStartX;
        this.translateY = e.clientY - this.panStartY;
        this.applyTransform();
    }

    onMouseUp(e) {
        if (!this.isActive) return;

        if (this.isPanning) {
            this.isPanning = false;
            this.canvasContainer.style.cursor = 'grab';
        }
    }

    onWheel(e) {
        if (!this.isActive) return;

        e.preventDefault();

        // Zoom based on wheel direction
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newScale = Math.max(0.1, Math.min(5.0, this.scale + delta));

        // Zoom towards mouse position
        const rect = this.canvasContainer.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Calculate new translate to keep mouse position fixed
        this.translateX = mouseX - (mouseX - this.translateX) * (newScale / this.scale);
        this.translateY = mouseY - (mouseY - this.translateY) * (newScale / this.scale);

        this.scale = newScale;
        this.applyTransform();
    }

    zoomIn() {
        this.scale = Math.min(5.0, this.scale + 0.2);
        this.applyTransform();
    }

    zoomOut() {
        this.scale = Math.max(0.1, this.scale - 0.2);
        this.applyTransform();
    }

    resetZoom() {
        this.scale = 1.0;
        this.translateX = 0;
        this.translateY = 0;
        this.applyTransform();
    }

    panWithArrows(key) {
        const panStep = 50;

        switch(key) {
            case 'ArrowLeft':
                this.translateX += panStep;
                break;
            case 'ArrowRight':
                this.translateX -= panStep;
                break;
            case 'ArrowUp':
                this.translateY += panStep;
                break;
            case 'ArrowDown':
                this.translateY -= panStep;
                break;
        }

        this.applyTransform();
    }

    toggleNumbers() {
        this.showNumbers = !this.showNumbers;
        this.visualizer.setShowNumbers(this.showNumbers);
        this.visualizer.renderCurrentMode(); // Re-render with new setting
    }

    toggleGrid() {
        this.showGrid = !this.showGrid;

        if (this.showGrid) {
            this.gridCanvas.style.display = 'block';
            this.drawGrid();
        } else {
            this.gridCanvas.style.display = 'none';
        }
    }

    setGridType(type) {
        this.gridType = type;
        this.showGrid = true;
        this.gridCanvas.style.display = 'block';
        this.drawGrid();
    }

    updateGridCanvas() {
        // Match grid canvas size to main canvas
        this.gridCanvas.width = this.canvas.width;
        this.gridCanvas.height = this.canvas.height;

        if (this.showGrid) {
            this.drawGrid();
        }
    }

    drawGrid() {
        const ctx = this.gridCanvas.getContext('2d');
        const width = this.gridCanvas.width;
        const height = this.gridCanvas.height;

        // Clear grid
        ctx.clearRect(0, 0, width, height);

        // Parse grid type
        const match = this.gridType.match(/(\d+)x(\d+)/);
        if (!match) return;

        const cols = parseInt(match[1]);
        const rows = parseInt(match[2]);

        // Grid settings
        ctx.strokeStyle = 'rgba(255, 0, 0, 0.7)';
        ctx.lineWidth = 3;
        ctx.setLineDash([10, 5]);

        // Draw vertical lines
        for (let i = 1; i < cols; i++) {
            const x = (width / cols) * i;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
        }

        // Draw horizontal lines
        for (let i = 1; i < rows; i++) {
            const y = (height / rows) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }

        // Draw labels
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(255, 0, 0, 0.9)';
        ctx.font = 'bold 24px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        for (let row = 0; row < rows; row++) {
            for (let col = 0; col < cols; col++) {
                const x = (width / cols) * (col + 0.5);
                const y = (height / rows) * (row + 0.5);
                const label = String.fromCharCode(65 + row) + (col + 1); // A1, A2, B1, B2, etc.

                // Draw label background
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.fillRect(x - 30, y - 20, 60, 40);

                // Draw label text
                ctx.fillStyle = 'rgba(255, 0, 0, 0.9)';
                ctx.fillText(label, x, y);
            }
        }
    }

    applyTransform() {
        // Apply transform to canvas container (contains both canvas and grid)
        this.canvasContainer.style.transform = `translate(${this.translateX}px, ${this.translateY}px) scale(${this.scale})`;
        this.canvasContainer.style.transformOrigin = 'center center';
    }

    destroy() {
        this.deactivate();

        // Cleanup
        if (this.mouseActivityTimeout) {
            clearTimeout(this.mouseActivityTimeout);
        }

        if (this.fullscreenContainer && this.fullscreenContainer.parentElement) {
            document.body.removeChild(this.fullscreenContainer);
        }
    }
}
