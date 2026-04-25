# Pulse: EV Charging Dashboard

Pulse is a Flask-based EV charging dashboard that predicts an EV charging priority score and visualizes cost, savings, grid impact, and CO2 offset in a simple single-page interface.

## Project Structure

```text
.
├── app.py
├── data/
├── docs/
├── models/
├── scripts/
├── static/
├── templates/
├── Procfile
├── railway.toml
├── requirements.txt
└── runtime.txt
```

## What the App Does

- Accepts charging capacity, battery capacity, state of charge, usage, and mode
- Predicts a priority score with a saved XGBoost model
- Calculates cost, savings, grid load impact, and CO2 offset
- Shows the result in a clean dashboard view

## Run Locally

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Start the app:

   ```bash
   python app.py
   ```

3. Open:

   ```text
   http://localhost:5000
   ```

## Health Check

You can test the backend with:

```bash
curl http://127.0.0.1:5000/health
```

## Model Notes

- The app loads the model from `models/nova_model.pkl`
- The training script is in `scripts/train_model.py`
- The dataset used for this demo is stored at `data/pulse_dataset.csv`

## Railway Deploy

- Railway guide: [docs/railway-deploy.md](docs/railway-deploy.md)
- Procfile included
- `railway.toml` included
- Healthcheck endpoint: `/health`
