// Utility functions

// Convert RGB to HEX
function rgbToHex(r, g, b) {
    return "#" + [r, g, b].map(x => {
        const hex = Math.round(x).toString(16);
        return hex.length === 1 ? "0" + hex : hex;
    }).join('');
}

// Convert HEX to RGB
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

// Calculate color distance (Euclidean)
function colorDistance(c1, c2) {
    return Math.sqrt(
        Math.pow(c1.r - c2.r, 2) +
        Math.pow(c1.g - c2.g, 2) +
        Math.pow(c1.b - c2.b, 2)
    );
}

// Get contrasting text color (black or white) for a background color
function getContrastColor(hexColor) {
    const rgb = hexToRgb(hexColor);
    if (!rgb) return '#000000';

    // Calculate relative luminance
    const luminance = (0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b) / 255;
    return luminance > 0.5 ? '#000000' : '#ffffff';
}

// Generate a nice color name based on RGB values
function generateColorName(r, g, b) {
    const colorNames = [
        { name: 'Rood', range: { r: [200, 255], g: [0, 100], b: [0, 100] } },
        { name: 'Groen', range: { r: [0, 100], g: [200, 255], b: [0, 100] } },
        { name: 'Blauw', range: { r: [0, 100], g: [0, 100], b: [200, 255] } },
        { name: 'Geel', range: { r: [200, 255], g: [200, 255], b: [0, 100] } },
        { name: 'Oranje', range: { r: [200, 255], g: [100, 200], b: [0, 100] } },
        { name: 'Paars', range: { r: [100, 200], g: [0, 100], b: [200, 255] } },
        { name: 'Roze', range: { r: [200, 255], g: [100, 200], b: [200, 255] } },
        { name: 'Cyaan', range: { r: [0, 100], g: [200, 255], b: [200, 255] } },
        { name: 'Bruin', range: { r: [100, 200], g: [50, 150], b: [0, 100] } },
        { name: 'Wit', range: { r: [200, 255], g: [200, 255], b: [200, 255] } },
        { name: 'Zwart', range: { r: [0, 80], g: [0, 80], b: [0, 80] } },
        { name: 'Grijs', range: { r: [80, 200], g: [80, 200], b: [80, 200] } }
    ];

    for (let colorDef of colorNames) {
        const { range } = colorDef;
        if (r >= range.r[0] && r <= range.r[1] &&
            g >= range.g[0] && g <= range.g[1] &&
            b >= range.b[0] && b <= range.b[1]) {
            return colorDef.name;
        }
    }

    return 'Kleur';
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Download file helper
function downloadFile(data, filename, type) {
    const blob = new Blob([data], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// Canvas to Blob
function canvasToBlob(canvas) {
    return new Promise((resolve) => {
        canvas.toBlob(resolve);
    });
}

// Clone object deeply
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

// Loading indicator functions
function showLoading(step = 'Bezig...') {
    const overlay = document.getElementById('loadingOverlay');
    const stepElement = document.getElementById('loadingStep');
    if (overlay) {
        overlay.classList.add('active');
        if (stepElement) {
            stepElement.textContent = step;
        }
        resetProgress(); // Reset progress bar when showing loading
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

function updateLoadingStep(step) {
    const stepElement = document.getElementById('loadingStep');
    if (stepElement) {
        stepElement.textContent = step;
    }
}

function updateProgress(percent, message) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const stepElement = document.getElementById('loadingStep');

    if (progressFill) {
        progressFill.style.width = `${percent}%`;
    }

    if (progressText) {
        progressText.textContent = `${Math.round(percent)}%`;
    }

    if (message && stepElement) {
        stepElement.textContent = message;
    }
}

function resetProgress() {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    if (progressFill) {
        progressFill.style.width = '0%';
    }

    if (progressText) {
        progressText.textContent = '0%';
    }
}

// Async wrapper with loading indicator
async function withLoading(asyncFunc, initialStep = 'Bezig...') {
    showLoading(initialStep);
    try {
        const result = await asyncFunc();
        return result;
    } finally {
        hideLoading();
    }
}
