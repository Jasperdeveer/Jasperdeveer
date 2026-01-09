// Presentation Mode for beamer projection workflow
// Features: Fullscreen, Zoom/Pan, Auto-fading keyboard shortcuts overlay

class PresentationMode {
    constructor(canvas, visualizer) {
        this.canvas = canvas;
        this.visualizer = visualizer;
        this.isFullscreen = false;
        this.isPanning = false;
        this.showNumbers = true;
        this.showGrid = false;

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

        // Keyboard shortcuts overlay element
        this.shortcutsOverlay = null;

        this.initialize();
    }

    initialize() {
        // Create shortcuts overlay
        this.createShortcutsOverlay();

        // Add event listeners
        this.addEventListeners();

        // Apply initial transform
        this.applyTransform();
    }

    createShortcutsOverlay() {
        // Create overlay element
        this.shortcutsOverlay = document.createElement('div');
        this.shortcutsOverlay.className = 'keyboard-shortcuts-overlay';
        this.shortcutsOverlay.innerHTML = `
            <div class="shortcuts-content">
                <h3>⌨️ Keyboard Shortcuts</h3>
                <div class="shortcuts-grid">
                    <div class="shortcut-item">
                        <kbd>F11</kbd> of <kbd>F</kbd>
                        <span>Fullscreen toggle</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>Space</kbd>
                        <span>Pan mode (hold + drag)</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>+</kbd> / <kbd>-</kbd>
                        <span>Zoom in/out</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>0</kbd>
                        <span>Reset zoom</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>N</kbd>
                        <span>Toggle numbers</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>G</kbd>
                        <span>Toggle grid</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>ESC</kbd>
                        <span>Exit fullscreen</span>
                    </div>
                    <div class="shortcut-item">
                        <kbd>←</kbd> <kbd>→</kbd> <kbd>↑</kbd> <kbd>↓</kbd>
                        <span>Pan canvas</span>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(this.shortcutsOverlay);
    }

    addEventListeners() {
        // Mouse movement detection
        document.addEventListener('mousemove', (e) => this.onMouseMove(e));

        // Keyboard events
        document.addEventListener('keydown', (e) => this.onKeyDown(e));
        document.addEventListener('keyup', (e) => this.onKeyUp(e));

        // Mouse events for panning
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        document.addEventListener('mousemove', (e) => this.onMouseDrag(e));
        document.addEventListener('mouseup', (e) => this.onMouseUp(e));

        // Wheel events for zooming
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));

        // Fullscreen change detection
        document.addEventListener('fullscreenchange', () => this.onFullscreenChange());
        document.addEventListener('webkitfullscreenchange', () => this.onFullscreenChange());
    }

    onMouseMove(e) {
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
        // Clear existing timer
        if (this.mouseActivityTimeout) {
            clearTimeout(this.mouseActivityTimeout);
        }

        // Set new timer to hide shortcuts after inactivity
        this.mouseActivityTimeout = setTimeout(() => {
            this.hideShortcuts();
        }, this.inactivityDelay);
    }

    onKeyDown(e) {
        // F or F11 - Toggle fullscreen
        if (e.key === 'f' || e.key === 'F' || e.key === 'F11') {
            e.preventDefault();
            this.toggleFullscreen();
        }

        // ESC - Exit fullscreen
        if (e.key === 'Escape' && this.isFullscreen) {
            this.exitFullscreen();
        }

        // Space - Enable pan mode
        if (e.key === ' ' || e.code === 'Space') {
            e.preventDefault();
            this.canvas.style.cursor = 'grab';
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

        // Arrow keys - Pan
        if (e.key.startsWith('Arrow')) {
            e.preventDefault();
            this.panWithArrows(e.key);
        }
    }

    onKeyUp(e) {
        // Space released - Disable pan mode
        if (e.key === ' ' || e.code === 'Space') {
            this.canvas.style.cursor = 'default';
        }
    }

    onMouseDown(e) {
        // Start panning if space is pressed
        if (e.button === 0) { // Left click
            this.isPanning = true;
            this.panStartX = e.clientX - this.translateX;
            this.panStartY = e.clientY - this.translateY;
            this.canvas.style.cursor = 'grabbing';
        }
    }

    onMouseDrag(e) {
        if (this.isPanning) {
            this.translateX = e.clientX - this.panStartX;
            this.translateY = e.clientY - this.panStartY;
            this.applyTransform();
        }
    }

    onMouseUp(e) {
        if (this.isPanning) {
            this.isPanning = false;
            this.canvas.style.cursor = 'default';
        }
    }

    onWheel(e) {
        e.preventDefault();

        // Zoom based on wheel direction
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newScale = Math.max(0.1, Math.min(5.0, this.scale + delta));

        // Zoom towards mouse position
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Calculate new translate to keep mouse position fixed
        this.translateX = mouseX - (mouseX - this.translateX) * (newScale / this.scale);
        this.translateY = mouseY - (mouseY - this.translateY) * (newScale / this.scale);

        this.scale = newScale;
        this.applyTransform();
    }

    toggleFullscreen() {
        if (!this.isFullscreen) {
            this.enterFullscreen();
        } else {
            this.exitFullscreen();
        }
    }

    enterFullscreen() {
        const elem = document.documentElement;

        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen();
        } else if (elem.mozRequestFullScreen) {
            elem.mozRequestFullScreen();
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen();
        }
    }

    exitFullscreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }

    onFullscreenChange() {
        this.isFullscreen = !!(document.fullscreenElement ||
                               document.webkitFullscreenElement ||
                               document.mozFullScreenElement ||
                               document.msFullscreenElement);
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
        // TODO: Implement number visibility toggle in visualizer
        console.log('Toggle numbers:', this.showNumbers);
    }

    toggleGrid() {
        this.showGrid = !this.showGrid;
        // TODO: Implement grid overlay
        console.log('Toggle grid:', this.showGrid);
    }

    applyTransform() {
        // Use CSS transforms for performant zoom/pan (GPU accelerated)
        this.canvas.style.transform = `translate(${this.translateX}px, ${this.translateY}px) scale(${this.scale})`;
        this.canvas.style.transformOrigin = '0 0';
    }

    destroy() {
        // Cleanup
        if (this.mouseActivityTimeout) {
            clearTimeout(this.mouseActivityTimeout);
        }

        if (this.shortcutsOverlay) {
            document.body.removeChild(this.shortcutsOverlay);
        }

        // Remove event listeners
        // (In production, we'd store references to bound functions for proper cleanup)
    }
}
