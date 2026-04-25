# Railway Deployment Guide

This project is ready to deploy on Railway as a single Flask web service.

## What is already prepared

- `app.py` listens on `0.0.0.0` and reads the Railway `PORT` variable
- `Procfile` uses `gunicorn` with `0.0.0.0:$PORT`
- `railway.toml` defines a start command and `/health` healthcheck
- `requirements.txt` lists the Python dependencies

## Before you deploy

1. Put this project in a GitHub repository.
2. Make sure these files are committed:
   - `app.py`
   - `models/nova_model.pkl`
   - `data/pulse_dataset.csv`
   - `templates/`
   - `static/`
   - `requirements.txt`
   - `Procfile`
   - `railway.toml`

## Deploy from GitHub

1. Sign in to Railway.
2. Create a new project.
3. Click `+ New` and choose `GitHub Repo`.
4. Select your repository.
5. Let Railway run the first build.
6. Open the service settings and confirm:
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - Healthcheck path: `/health`
7. Go to `Settings -> Networking -> Public Networking`.
8. Click `Generate Domain`.
9. Open the generated URL and verify the dashboard loads.

## Optional checks after deploy

- Visit `/health` and confirm it returns `200`
- Run one prediction in the browser and confirm the numbers update
- Check Railway deployment logs for missing files or Python package errors

## Deploy from the CLI

1. Install the Railway CLI.
2. Run `railway login`
3. Run `railway link` inside the project folder
4. Run `railway up`
5. After deploy, generate a public domain in the Railway dashboard

## If the deploy fails

- If Railway says it cannot find a start command, keep `railway.toml` and the `Procfile` committed.
- If the app fails healthchecks, confirm the service is using `/health`.
- If the app starts but the page is broken, check that `models/nova_model.pkl` was included in the deployed repo.
