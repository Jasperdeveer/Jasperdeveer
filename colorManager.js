// Color palette management with undo functionality

class ColorManager {
    constructor() {
        this.colors = [];
        this.history = [];
        this.maxHistory = 20;
        this.previewColorIndex = null;
    }

    setColors(colors) {
        this.saveHistory();
        this.colors = colors.map((c, index) => ({
            ...c,
            number: index + 1
        }));
    }

    getColors() {
        return this.colors;
    }

    addColor(color) {
        this.saveHistory();
        const newColor = {
            ...color,
            id: Date.now(),
            number: this.colors.length + 1
        };
        this.colors.push(newColor);
        this.renumberColors();
        return newColor;
    }

    removeColor(colorId) {
        this.saveHistory();
        this.colors = this.colors.filter(c => c.id !== colorId);
        this.renumberColors();
    }

    renameColor(colorId, newName) {
        this.saveHistory();
        const color = this.colors.find(c => c.id === colorId);
        if (color) {
            color.name = newName;
        }
    }

    updateColor(colorId, updates) {
        this.saveHistory();
        const colorIndex = this.colors.findIndex(c => c.id === colorId);
        if (colorIndex !== -1) {
            this.colors[colorIndex] = {
                ...this.colors[colorIndex],
                ...updates
            };
        }
    }

    renumberColors() {
        this.colors.forEach((color, index) => {
            color.number = index + 1;
        });
    }

    saveHistory() {
        this.history.push(deepClone(this.colors));
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        }
    }

    undo() {
        if (this.history.length > 0) {
            this.colors = this.history.pop();
            return true;
        }
        return false;
    }

    canUndo() {
        return this.history.length > 0;
    }

    setPreviewColor(colorIndex) {
        this.previewColorIndex = colorIndex;
    }

    clearPreview() {
        this.previewColorIndex = null;
    }

    isPreviewActive() {
        return this.previewColorIndex !== null;
    }

    getPreviewColorIndex() {
        return this.previewColorIndex;
    }

    // Redistribute colors evenly after changes
    redistributeColors(imageProcessor, numColors) {
        if (!imageProcessor || !imageProcessor.imageData) return;

        const newColors = imageProcessor.detectColors(numColors);
        this.setColors(newColors);
        return newColors;
    }

    // Get color by index
    getColorByIndex(index) {
        return this.colors[index];
    }

    // Get color by ID
    getColorById(id) {
        return this.colors.find(c => c.id === id);
    }

    // Calculate total number of colors
    getColorCount() {
        return this.colors.length;
    }

    // Export colors as array
    exportColors() {
        return this.colors.map(c => ({
            number: c.number,
            name: c.name,
            hex: c.hex,
            rgb: { r: c.r, g: c.g, b: c.b }
        }));
    }

    // Import colors from array
    importColors(colorArray) {
        this.saveHistory();
        this.colors = colorArray.map((c, index) => ({
            id: Date.now() + index,
            number: index + 1,
            name: c.name || generateColorName(c.rgb.r, c.rgb.g, c.rgb.b),
            hex: c.hex,
            r: c.rgb.r,
            g: c.rgb.g,
            b: c.rgb.b
        }));
    }
}
