import os
from pathlib import Path
import pickle

import numpy as np
from flask import Flask, jsonify, render_template, request


# This finds the main project folders once so the app can reuse them everywhere.
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "nova_model.pkl"

# These are the default values used when the form does not send optional fields.
DEFAULT_MODEL_INPUTS = {
    "cost_per_kWh": 8.0,
    "charger_type": "DC Fast",
    "renewable_energy": "Yes",
    "maintenance_frequency": "Monthly",
    "latitude": 12.97,
    "longitude": 80.24,
}

app = Flask(__name__)


# This fills in a few missing model settings so older saved XGBoost files still work.
def ensure_model_compatibility(model):
    if model is None:
        return None

    compatibility_defaults = {
        "gpu_id": None,
        "predictor": None,
    }
    for attribute, value in compatibility_defaults.items():
        if not hasattr(model, attribute):
            setattr(model, attribute, value)

    return model


# This loads the saved model file and its extra metadata from disk.
def load_model(model_path):
    try:
        with model_path.open("rb") as model_file:
            metadata = pickle.load(model_file)
    except FileNotFoundError:
        print(f"Error: {model_path} not found. Run scripts/train_model.py first.")
        return None, [], {}, {}

    return (
        ensure_model_compatibility(metadata.get("model")),
        metadata.get("features", []),
        metadata.get("encoders", {}),
        metadata,
    )


# This loads the model once when the Flask app starts.
nova_model, feature_names, encoders, model_metadata = load_model(MODEL_PATH)


# This estimates session cost and eco-mode savings from the battery energy still needed.
def calculate_financials(capacity, soc, mode):
    base_rate = 8.0
    energy_needed = capacity * (1 - (soc / 100))
    if mode == "eco":
        cost = energy_needed * (base_rate * 0.8)
        savings = energy_needed * (base_rate * 0.2)
    else:
        cost = energy_needed * base_rate
        savings = 0
    return round(cost, 2), round(savings, 2)


# This turns the model score into a simple standard-vs-optimized grid load comparison.
def calculate_grid_impact(capacity, priority_score):
    standard_stress = capacity * 0.8
    normalized_priority = np.clip(priority_score / 100, 0, 1)
    reduction_rate = 0.9 - (0.18 * normalized_priority)
    optimized_stress = standard_stress * reduction_rate
    return round(standard_stress, 1), round(optimized_stress, 1)


# This converts the money saved into a rough CO2 saving for the dashboard.
def calculate_co2_saved(savings):
    return round(savings * 0.4, 2)


# This trims odd edge-case scores so a nearly full battery does not show fake urgency.
def calibrate_priority_score(priority_score, state_of_charge):
    if state_of_charge >= 99.5:
        return 0.0
    return float(np.clip(priority_score, 0, 100))


# This converts text categories like charger type into the numeric values the model expects.
def encode_categorical_feature(name, value):
    classes = encoders.get(name, [])
    if value in classes:
        return classes.index(value)
    if classes:
        return 0
    return value


# This gathers form inputs and arranges them into the exact feature order used by the model.
def build_feature_vector(payload):
    charging_capacity = float(payload.get("charging_capacity", 150))
    battery_capacity = float(payload.get("battery_capacity", 75))
    state_of_charge = float(payload.get("state_of_charge", 50))
    usage_stats = float(payload.get("usage_stats", 40))
    mode = payload.get("mode", "fast")

    input_values = {
        **DEFAULT_MODEL_INPUTS,
        "charging_capacity_kW": charging_capacity,
        "usage_stats": usage_stats,
        "battery_capacity": battery_capacity,
        "state_of_charge": state_of_charge,
    }
    for feature_name in ("charger_type", "renewable_energy", "maintenance_frequency"):
        input_values[feature_name] = encode_categorical_feature(
            feature_name,
            payload.get(feature_name, DEFAULT_MODEL_INPUTS[feature_name]),
        )

    features = [input_values.get(column, 0) for column in feature_names]

    return (
        np.array([features]),
        charging_capacity,
        battery_capacity,
        state_of_charge,
        usage_stats,
        mode,
    )


# This serves the main dashboard page and passes a few model details to the template.
@app.get("/")
def index():
    return render_template(
        "index.html",
        model_rmse=model_metadata.get("rmse"),
        training_source=model_metadata.get("training_source", "unknown"),
    )


# This gives Railway and local checks a quick way to confirm the app is alive.
@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "model_loaded": nova_model is not None,
            "model_path": str(MODEL_PATH.relative_to(BASE_DIR)),
            "feature_count": len(feature_names),
        }
    )


# This receives dashboard inputs, runs the model, and sends back the numbers the UI shows.
@app.post("/predict")
def predict():
    try:
        payload = request.get_json(silent=True) or {}

        if nova_model is None:
            return jsonify({"success": False, "error": "Model not loaded."}), 500

        feature_vector, charging_capacity, battery_capacity, soc, _, mode = build_feature_vector(payload)
        priority_score = calibrate_priority_score(nova_model.predict(feature_vector)[0], soc)

        cost, savings = calculate_financials(battery_capacity, soc, mode)
        standard_stress, optimized_stress = calculate_grid_impact(charging_capacity, priority_score)
        co2_saved = calculate_co2_saved(savings)

        return jsonify(
            {
                "success": True,
                "priority_score": round(priority_score, 2),
                "cost": cost,
                "savings": savings,
                "co2_saved": co2_saved,
                "grid_impact": {
                    "standard": standard_stress,
                    "optimized": optimized_stress,
                },
            }
        )
    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 500


# This starts the Flask server and lets Railway provide the real port in production.
if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
