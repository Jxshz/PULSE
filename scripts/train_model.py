from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


# This points the script to the main project folders so it saves files in the right place.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "pulse_dataset.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "nova_model.pkl"

# These are the exact columns used to train and later run the prediction model.
FEATURES = [
    "charging_capacity_kW",
    "usage_stats",
    "cost_per_kWh",
    "battery_capacity",
    "state_of_charge",
    "charger_type",
    "renewable_energy",
    "maintenance_frequency",
    "latitude",
    "longitude",
]
TARGET = "priority_score"
CATEGORICAL_COLUMNS = ["charger_type", "renewable_energy", "maintenance_frequency"]


# This creates a clean training target so the score follows simple EV charging logic.
def calculate_priority_score(dataframe):
    soc_gap = 1 - (dataframe["state_of_charge"] / 100)
    energy_needed = dataframe["battery_capacity"] * soc_gap
    energy_need_factor = energy_needed / 150
    usage_factor = dataframe["usage_stats"] / 100
    charger_factor = dataframe["charging_capacity_kW"] / 350
    battery_factor = dataframe["battery_capacity"] / 150

    charger_bonus = dataframe["charger_type"].map(
        {"Level 1": 0.01, "Level 2": 0.03, "DC Fast": 0.05}
    )
    renewable_bonus = dataframe["renewable_energy"].map({"No": 0.0, "Yes": 0.03})
    maintenance_bonus = dataframe["maintenance_frequency"].map(
        {"Quarterly": 0.01, "Monthly": 0.02, "Weekly": 0.03}
    )

    raw_score = (
        0.68 * energy_need_factor
        + 0.14 * usage_factor * soc_gap
        + 0.08 * charger_factor * soc_gap
        + 0.04 * battery_factor * soc_gap
        + charger_bonus * soc_gap
        + renewable_bonus * soc_gap
        + maintenance_bonus * soc_gap
    )

    return np.round(np.clip(raw_score * 100, 0, 100), 2)


# This builds a synthetic dataset when a real competition dataset is not available yet.
def build_demo_dataset():
    np.random.seed(42)
    n_samples = 2500

    dataframe = pd.DataFrame(
        {
            "charging_capacity_kW": np.random.uniform(0, 350, n_samples),
            "usage_stats": np.random.uniform(0, 100, n_samples),
            "cost_per_kWh": np.random.uniform(6.5, 10.0, n_samples),
            "battery_capacity": np.random.uniform(20, 150, n_samples),
            "state_of_charge": np.random.uniform(0, 100, n_samples),
            "charger_type": np.random.choice(["Level 1", "Level 2", "DC Fast"], n_samples),
            "renewable_energy": np.random.choice(["Yes", "No"], n_samples),
            "maintenance_frequency": np.random.choice(["Weekly", "Monthly", "Quarterly"], n_samples),
            "latitude": np.random.uniform(10, 20, n_samples),
            "longitude": np.random.uniform(75, 85, n_samples),
        }
    )
    dataframe[TARGET] = calculate_priority_score(dataframe)
    return dataframe


# This loads the saved dataset if it exists, or creates one so training can still run.
def load_training_data():
    if DATA_PATH.exists():
        print(f"Using dataset from {DATA_PATH}")
        return pd.read_csv(DATA_PATH)

    print("No data/pulse_dataset.csv found, generating a synthetic demo dataset instead.")
    dataframe = build_demo_dataset()
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(DATA_PATH, index=False)
    print(f"Synthetic dataset saved to {DATA_PATH}")
    return dataframe


# This turns text categories into numbers so XGBoost can learn from them.
def encode_categories(dataframe):
    encoders = {}
    for column in CATEGORICAL_COLUMNS:
        encoder = LabelEncoder()
        dataframe[column] = encoder.fit_transform(dataframe[column])
        encoders[column] = list(encoder.classes_)
    return dataframe, encoders


# This trains the model, measures it, and saves everything the Flask app needs.
def main():
    dataframe = load_training_data()
    dataframe, encoders = encode_categories(dataframe)

    X_train, X_test, y_train, y_test = train_test_split(
        dataframe[FEATURES],
        dataframe[TARGET],
        test_size=0.2,
        random_state=42,
    )

    model = xgb.XGBRegressor(
        n_estimators=240,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    rmse = float(mean_squared_error(y_test, predictions, squared=False))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "model": model,
        "encoders": encoders,
        "features": FEATURES,
        "rmse": round(rmse, 4),
        "model_version": "priority-v2",
        "training_source": "synthetic_domain_informed",
    }

    with MODEL_PATH.open("wb") as model_file:
        pickle.dump(metadata, model_file)

    print(f"Model trained and saved to {MODEL_PATH}")
    print(f"Validation RMSE: {rmse:.4f}")


# This lets the script run directly from the terminal.
if __name__ == "__main__":
    main()
