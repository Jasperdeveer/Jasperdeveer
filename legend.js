// Legend and spray paint calculations

class Legend {
    constructor(legendElement, sprayResultsElement) {
        this.legendElement = legendElement;
        this.sprayResultsElement = sprayResultsElement;
        this.canvasWidth = 100; // cm
        this.canvasHeight = 100; // cm
        this.sprayCanCoverage = 2.25; // m² per can (average of 2-2.5)
    }

    setCanvasDimensions(width, height) {
        this.canvasWidth = width;
        this.canvasHeight = height;
    }

    render(colors, regionStats) {
        this.renderLegend(colors, regionStats);
        this.renderSprayCalculations(colors, regionStats);
    }

    renderLegend(colors, regionStats) {
        if (!colors || colors.length === 0) {
            this.legendElement.innerHTML = '<p style="color: #999;">Geen kleuren gedetecteerd</p>';
            return;
        }

        let html = '';

        colors.forEach((color, index) => {
            const stats = regionStats ? regionStats.find(s => s.colorIndex === index) : null;
            const percentage = stats ? stats.percentage : 0;
            const pixelCount = stats ? stats.pixelCount : 0;

            html += `
                <div class="legend-item">
                    <div class="legend-number">${color.number}</div>
                    <div class="legend-swatch" style="background-color: ${color.hex}"></div>
                    <div class="legend-info">
                        <div class="legend-name">${color.name}</div>
                        <div class="legend-stats">${percentage}% • ${pixelCount.toLocaleString()} px</div>
                    </div>
                </div>
            `;
        });

        this.legendElement.innerHTML = html;
    }

    renderSprayCalculations(colors, regionStats) {
        if (!colors || colors.length === 0 || !regionStats) {
            this.sprayResultsElement.innerHTML = '<p style="color: #999;">Geen data beschikbaar</p>';
            return;
        }

        // Calculate total canvas area in m²
        const totalAreaM2 = (this.canvasWidth * this.canvasHeight) / 10000;

        let html = '';
        let totalCans = 0;

        colors.forEach((color, index) => {
            const stats = regionStats.find(s => s.colorIndex === index);
            if (!stats) return;

            // Calculate area for this color
            const colorAreaM2 = totalAreaM2 * (parseFloat(stats.percentage) / 100);

            // Calculate cans needed (rounded up)
            const cansNeeded = Math.ceil(colorAreaM2 / this.sprayCanCoverage);

            totalCans += cansNeeded;

            html += `
                <div class="spray-item">
                    <div class="spray-color" style="background-color: ${color.hex}"></div>
                    <div class="spray-text">
                        ${color.number}. ${color.name}<br>
                        <small>${colorAreaM2.toFixed(3)} m²</small>
                    </div>
                    <div class="spray-cans">${cansNeeded} bus${cansNeeded !== 1 ? 'sen' : ''}</div>
                </div>
            `;
        });

        html += `
            <div class="total-cans">
                Totaal: ${totalCans} spuitbus${totalCans !== 1 ? 'sen' : ''}<br>
                <small>Voor ${totalAreaM2.toFixed(2)} m² (${this.canvasWidth}×${this.canvasHeight} cm)</small>
            </div>
        `;

        this.sprayResultsElement.innerHTML = html;
    }

    updateDimensions(width, height) {
        this.setCanvasDimensions(width, height);
    }
}
