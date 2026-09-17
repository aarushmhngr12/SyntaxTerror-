# GlucoGuard

A multi-patient diabetes care monitoring dashboard backed by Excel data and a rule-based, explainable signal engine.

## Run

```bash
pip install -r requirements.txt
python web_app.py
```

Open `http://127.0.0.1:5000`.

## Pages

- `/` — landing page
- `/patients` — searchable patient directory
- `/patient/P001` — individual patient dashboard
- `/patient/<patient_id>/run-monitoring` — process a new glucose signal for that patient

## Data

The dashboard reads from `diabetes_adherence_data.xlsx`.

The workbook contains five demo patients (P001–P005), with patient information, baselines, glucose/activity/sleep events, refill history and HbA1c results.
