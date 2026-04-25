// This keeps each slider and number field in sync so both inputs show the same value.
function syncInputs(rangeId, numberId, onChange) {
    const range = document.getElementById(rangeId);
    const number = document.getElementById(numberId);

    const updateValue = (value) => {
        range.value = value;
        number.value = value;
        if (onChange) {
            onChange(parseFloat(value));
        }
    };

    range.addEventListener("input", () => updateValue(range.value));
    number.addEventListener("input", () => updateValue(number.value));
}

// This creates the main grid impact chart shown near the bottom of the dashboard.
const ctx = document.getElementById("impactChart").getContext("2d");
const impactChart = new Chart(ctx, {
    type: "bar",
    data: {
        labels: ["Standard Load", "Optimized Load"],
        datasets: [
            {
                label: "Grid Load (%)",
                data: [0, 0],
                backgroundColor: ["#d1d5db", "#3B82F6"],
                borderColor: ["#9ca3af", "#2563eb"],
                borderWidth: 1,
                borderRadius: 18,
                borderSkipped: false,
                maxBarThickness: 48,
            },
        ],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        scales: {
            x: {
                beginAtZero: true,
                max: 140,
                ticks: {
                    color: "#374151",
                },
                grid: {
                    color: "#f3f4f6",
                },
            },
            y: {
                ticks: {
                    color: "#374151",
                },
                grid: {
                    display: false,
                },
            },
        },
        plugins: {
            legend: {
                display: false,
            },
            title: {
                display: true,
                text: "Predicted Grid Load Impact",
                color: "#374151",
                font: {
                    size: 16,
                    weight: "bold",
                },
            },
        },
        animation: {
            duration: 1500,
            easing: "easeInOutQuart",
        },
    },
});

// This updates the chart cards and bars from one shared set of grid values.
function renderGridImpact(gridImpact, note) {
    const standard = Math.round(gridImpact.standard * 10) / 10;
    const optimized = Math.round(gridImpact.optimized * 10) / 10;
    const reductionRate = standard > 0 ? ((standard - optimized) / standard) * 100 : 0;
    const axisMax = Math.max(140, Math.ceil((Math.max(standard, optimized) * 1.15) / 10) * 10);

    impactChart.data.datasets[0].data = [standard, optimized];
    impactChart.options.scales.x.max = axisMax;
    impactChart.update();

    document.getElementById("standard-load-value").textContent = `${standard.toFixed(1)}%`;
    document.getElementById("optimized-load-value").textContent = `${optimized.toFixed(1)}%`;
    document.getElementById("reduction-rate-value").textContent = `${reductionRate.toFixed(1)}%`;
    document.getElementById("grid-impact-note").textContent = note;
}

// This gives a quick live chart preview before the user runs a full prediction.
function updateImpactChart(chargingCapacity) {
    const standardLoad = Math.min(140, 40 + (chargingCapacity / 350) * 80);
    const optimizedLoad = Math.max(0, standardLoad * 0.75);
    renderGridImpact(
        {
            standard: standardLoad,
            optimized: optimizedLoad,
        },
        "Live preview estimates the grid load from charging capacity before you run the full prediction."
    );
}

// This replaces the preview with the real backend numbers after prediction finishes.
function updateImpactChartFromPrediction(gridImpact) {
    const reductionRate = gridImpact.standard > 0
        ? ((gridImpact.standard - gridImpact.optimized) / gridImpact.standard) * 100
        : 0;

    renderGridImpact(
        gridImpact,
        `Prediction complete: Pulse trims the projected load by ${reductionRate.toFixed(1)}% for this charging scenario.`
    );
}

// This wires up all input pairs as soon as the page loads.
syncInputs("charging_range", "charging_number", updateImpactChart);
syncInputs("battery_range", "battery_number");
syncInputs("soc_range", "soc_number");
syncInputs("usage_range", "usage_number");

// This shows a useful chart preview even before the first prediction is made.
updateImpactChart(parseFloat(document.getElementById("charging_range").value));

// This grabs the main UI elements used by the interactions below.
const predictorForm = document.getElementById("predictor-form");
const predictButton = document.getElementById("predict-button");
const modeToggle = document.getElementById("mode-toggle");
const modeThumb = document.getElementById("mode-thumb");
const modeInput = document.getElementById("mode_input");
let currentMode = "fast";

// This switches the mode pill between fast and eco.
modeToggle.addEventListener("click", () => {
    currentMode = currentMode === "fast" ? "eco" : "fast";
    modeInput.value = currentMode;

    if (currentMode === "eco") {
        modeToggle.classList.add("bg-blue-600");
        modeThumb.style.transform = "translateX(1.5rem)";
        return;
    }

    modeToggle.classList.remove("bg-blue-600");
    modeThumb.style.transform = "translateX(0)";
});

// This makes the top action button submit the form like a normal app control.
predictButton.addEventListener("click", (event) => {
    event.preventDefault();
    predictorForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
});

// This sends the form data to Flask and paints the returned values onto the dashboard.
predictorForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(predictorForm);
    const data = Object.fromEntries(formData);

    try {
        const response = await fetch(predictorForm.dataset.predictUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.error || "Prediction API failed");
        }

        document.getElementById("score").textContent = result.priority_score.toFixed(2);
        document.getElementById("cost").textContent = `₹${result.cost.toFixed(2)}`;
        document.getElementById("savings").textContent = `₹${result.savings.toFixed(2)}`;
        document.getElementById("co2_saved").textContent = `${result.co2_saved.toFixed(2)} kg`;
        updateImpactChartFromPrediction(result.grid_impact);

        const scoreCard = document.getElementById("score-card");
        scoreCard.classList.add("animate");
        setTimeout(() => scoreCard.classList.remove("animate"), 650);
    } catch (error) {
        console.error("Prediction error:", error);
        alert("An error occurred while predicting.");
    }
});
