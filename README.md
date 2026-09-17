# GlucoGuard

### Diabetes Medication-Adherence Monitoring System

GlucoGuard is a monitoring system that identifies potential medication-adherence concerns by analyzing multiple patient signals, including glucose levels, refill behaviour, physical activity, sleep, and HbA1c trends.
The dashboard reads from `diabetes_adherence_data.xlsx`.

## Run

```bash
git clone https://github.com/aarushmhngr12/SyntaxTerror-.git
cd SyntaxTerror-
pip install -r requirements.txt
python web_app.py
```

Open `http://127.0.0.1:5000`.

## Pages

- `/` — landing page
- `/patients` — searchable patient directory
- `/patient/P001` — individual patient dashboard
- `/patient/<patient_id>/run-monitoring` — process a new glucose signal for that patient

The dashboard reads from `diabetes_adherence_data.xlsx`.

## Features

- 👥 Multi-patient monitoring
- 📊 Glucose & HbA1c trends
- 💊 Medication refill analysis
- 📈 Temporal refill–glucose analysis
- 💤 Activity & sleep context
- 🔍 Explainable monitoring alerts
- ⚡ Live signal simulation

## How It Works

```text
Patient Data
     ↓
Signal Analysis
     ↓
Adherence + Context Signals
     ↓
Temporal Analysis
     ↓
Monitoring State
     ↓
Explainable Dashboard
```

## Monitoring States

The system can classify patients as:

STABLE->
MONITOR->
WATCH->
POSSIBLE ADHERENCE CONCERN

Each state is accompanied by an explanation of the contributing signals.

## Tech Stack

Python · Flask · Pandas · Excel · HTML · CSS · JavaScript · Chart.js

## Data Disclaimer

All patient records are fictional demonstration data. GlucoGuard is a prototype and is not intended for medical diagnosis or treatment.


