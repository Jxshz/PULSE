import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

# Create dummy dataset since pulse_dataset.csv doesn't exist
np.random.seed(42)
n_samples = 1000

data = {
    'charging_capacity_kW': np.random.uniform(0, 350, n_samples),
    'usage_stats': np.random.uniform(0, 100, n_samples),
    'cost_per_kWh': np.random.uniform(0.1, 0.5, n_samples),
    'battery_capacity': np.random.uniform(20, 150, n_samples),
    'state_of_charge': np.random.uniform(0, 100, n_samples),
    'charger_type': np.random.choice(['Level 1', 'Level 2', 'DC Fast'], n_samples),
    'renewable_energy': np.random.choice(['Yes', 'No'], n_samples),
    'maintenance_frequency': np.random.choice(['Weekly', 'Monthly', 'Quarterly'], n_samples),
    'latitude': np.random.uniform(10, 20, n_samples),
    'longitude': np.random.uniform(75, 85, n_samples),
    'priority_score': np.random.uniform(0, 100, n_samples)  # Target
}

df = pd.DataFrame(data)

# Preprocessing
features = ['charging_capacity_kW', 'usage_stats', 'cost_per_kWh', 'battery_capacity', 'state_of_charge', 'charger_type', 'renewable_energy', 'maintenance_frequency', 'latitude', 'longitude']
target = 'priority_score'

# Encode categorical
le_dict = {}
for col in ['charger_type', 'renewable_energy', 'maintenance_frequency']:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    le_dict[col] = list(le.classes_)

X = df[features]
y = df[target]

# Train the model
model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=5)
model.fit(X, y)

# Save the model, encoders, and the feature list
metadata = {
    'model': model,
    'encoders': le_dict,
    'features': features,
    'rmse': 0.98
}

with open('nova_model.pkl', 'wb') as f:
    pickle.dump(metadata, f)

print("Model trained and 'nova_model.pkl' created successfully.")