import os
from flask import Flask, render_template, redirect, url_for, request
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.environ.get('DATA_FILE', os.path.join(BASE_DIR, 'diabetes_adherence_data.xlsx'))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))


def load_data():
    events = pd.read_excel(DATA_FILE, sheet_name='Patient_Events')
    refills = pd.read_excel(DATA_FILE, sheet_name='Refills')
    labs = pd.read_excel(DATA_FILE, sheet_name='Lab_Results')
    info = pd.read_excel(DATA_FILE, sheet_name='Patient_Info')
    baseline = pd.read_excel(DATA_FILE, sheet_name='Baseline')
    events['Timestamp'] = pd.to_datetime(events['Timestamp'])
    refills['Prescription_Date'] = pd.to_datetime(refills['Prescription_Date'])
    refills['Expected_Refill_Date'] = pd.to_datetime(refills['Expected_Refill_Date'])
    refills['Actual_Refill_Date'] = pd.to_datetime(refills['Actual_Refill_Date'])
    labs['Date'] = pd.to_datetime(labs['Date'])
    return events, refills, labs, info, baseline


def analyse_patient(patient_id):
    events, refills, labs, info, baseline = load_data()
    patient_row = info[info['Patient_ID'].astype(str) == str(patient_id)]
    if patient_row.empty:
        return None
    p = patient_row.iloc[0]
    b = baseline[baseline['Patient_ID'].astype(str) == str(patient_id)].iloc[0]
    pe = events[events['Patient_ID'].astype(str) == str(patient_id)].sort_values('Timestamp')
    pr = refills[refills['Patient_ID'].astype(str) == str(patient_id)].sort_values('Actual_Refill_Date')
    pl = labs[labs['Patient_ID'].astype(str) == str(patient_id)].sort_values('Date')

    normal_glucose = float(b['Avg_Glucose'])
    normal_steps = float(b['Avg_Steps'])
    normal_sleep = float(b['Avg_Sleep'])
    glucose_data = pe[pe['Event_Type'] == 'GLUCOSE'].sort_values('Timestamp')
    steps_data = pe[pe['Event_Type'] == 'STEPS'].sort_values('Timestamp')
    sleep_data = pe[pe['Event_Type'] == 'SLEEP'].sort_values('Timestamp')

    latest_glucose = float(glucose_data.iloc[-1]['Value'])
    latest_steps = float(steps_data.iloc[-1]['Value']) if not steps_data.empty else normal_steps
    latest_sleep = float(sleep_data.iloc[-1]['Value']) if not sleep_data.empty else normal_sleep
    glucose_deviation = latest_glucose - normal_glucose

    latest_delay = int(pr.iloc[-1]['Days_Delayed']) if not pr.empty else 0
    latest_refill_date = pr.iloc[-1]['Actual_Refill_Date'] if not pr.empty else pd.Timestamp.now()
    if len(pr) >= 2:
        prev_delay = int(pr.iloc[-2]['Days_Delayed'])
        refill_pattern = 'Worsening' if latest_delay > prev_delay else ('Stable' if latest_delay == prev_delay else 'Improving')
    else:
        refill_pattern = 'Not enough data'
    refill_trend = ' → '.join(str(int(x)) for x in pr['Days_Delayed']) if not pr.empty else 'No refill history'

    adherence_signals = int(glucose_deviation > 20) + int(latest_delay > 0)
    alternative_signals = int(latest_steps < normal_steps * 0.8) + int(latest_sleep < normal_sleep * 0.8)
    confidence = 'High' if adherence_signals == 2 and alternative_signals == 0 else ('Moderate' if adherence_signals == 2 else 'Low')

    before_start = latest_refill_date - pd.Timedelta(days=3)
    after_end = latest_refill_date + pd.Timedelta(days=3)
    before = glucose_data[(glucose_data['Timestamp'] >= before_start) & (glucose_data['Timestamp'] < latest_refill_date)]
    after = glucose_data[(glucose_data['Timestamp'] >= latest_refill_date) & (glucose_data['Timestamp'] <= after_end)]
    if len(before) and len(after):
        before_avg = float(before['Value'].mean())
        after_avg = float(after['Value'].mean())
        glucose_change = after_avg - before_avg
    else:
        before_avg = after_avg = glucose_change = 0.0
    temporal_pattern = 'Worsening after refill disruption' if glucose_change > 10 else 'No clear worsening pattern'
    temporal_signal = int(glucose_change > 10) + int(latest_delay > 0)

    if adherence_signals == 2 and refill_pattern == 'Worsening' and temporal_signal == 2:
        state = 'POSSIBLE ADHERENCE CONCERN'
        state_class = 'concern'
    elif adherence_signals == 2:
        state = 'WATCH'
        state_class = 'watch'
    elif adherence_signals == 1:
        state = 'MONITOR'
        state_class = 'monitor'
    else:
        state = 'STABLE'
        state_class = 'stable'

    latest_hba1c = float(pl.iloc[-1]['HbA1c']) if not pl.empty else 0.0
    previous_hba1c = float(pl.iloc[-2]['HbA1c']) if len(pl) >= 2 else latest_hba1c
    hba1c_change = latest_hba1c - previous_hba1c

    if state == 'POSSIBLE ADHERENCE CONCERN':
        reason_text = (f"Glucose is {glucose_deviation:+.1f} mg/dL from the patient's personal baseline, "
                       f"the latest refill was delayed by {latest_delay} days, and the refill pattern is "
                       f"{refill_pattern.lower()}. Glucose changed by {glucose_change:+.1f} mg/dL within "
                       "the 3-day before/after refill window. These connected signals may warrant clinical review.")
        suggested_action = 'Review medication access, treatment changes and adherence context during the next clinical interaction.'
    elif state == 'WATCH':
        reason_text = 'Multiple treatment-related signals are present, but the current evidence does not meet the criteria for a stronger adherence concern.'
        suggested_action = 'Continue monitoring refill, glucose and contextual signals.'
    elif state == 'MONITOR':
        reason_text = 'One treatment-related signal has changed. Continued monitoring will help determine whether a connected pattern develops.'
        suggested_action = 'Continue monitoring before drawing a stronger conclusion.'
    else:
        reason_text = 'The available treatment-related signals do not currently show a strong adherence-related pattern.'
        suggested_action = 'Continue routine monitoring and reassess if the pattern changes.'

    timeline = []
    for _, row in pr.iterrows():
        delay = int(row['Days_Delayed'])
        item_state = 'On time' if delay == 0 else ('Delayed' if delay <= 4 else 'Significant delay')
        timeline.append({'date': row['Actual_Refill_Date'].strftime('%d %b %Y'), 'delay': delay, 'state': item_state})

    recent_events = pe.sort_values('Timestamp', ascending=False).head(8)
    activity = []
    for _, row in recent_events.iterrows():
        activity.append({'type': row['Event_Type'], 'value': row['Value'], 'unit': row['Unit'], 'time': row['Timestamp'].strftime('%d %b %Y, %I:%M %p')})

    # Keep the chart readable while preserving the full history in the page data.
    glucose_labels = glucose_data['Timestamp'].dt.strftime('%d %b').tolist()
    glucose_values = glucose_data['Value'].astype(float).tolist()
    refill_labels = pr['Actual_Refill_Date'].dt.strftime('%d %b').tolist()
    refill_values = pr['Days_Delayed'].astype(float).tolist()

    return {
        'patient_id': str(p['Patient_ID']), 'name': str(p.get('Name', p['Patient_ID'])), 'age': int(p.get('Age', 0)),
        'gender': str(p.get('Gender', '')), 'age_group': str(p.get('Age_Group', '')), 'diabetes_type': str(p['Diabetes_Type']),
        'medication': str(p['Medication']), 'dose': str(p.get('Dose', '')), 'frequency': str(p.get('Frequency', '')),
        'registration_date': pd.to_datetime(p.get('Registration_Date', pd.Timestamp.now())).strftime('%d %b %Y'),
        'state': state, 'state_class': state_class, 'confidence': confidence,
        'reason_text': reason_text, 'suggested_action': suggested_action,
        'latest_glucose': latest_glucose, 'normal_glucose': normal_glucose, 'glucose_deviation': glucose_deviation,
        'latest_delay': latest_delay, 'refill_pattern': refill_pattern, 'refill_trend': refill_trend,
        'latest_steps': latest_steps, 'normal_steps': normal_steps, 'latest_sleep': latest_sleep, 'normal_sleep': normal_sleep,
        'adherence_signals': adherence_signals, 'alternative_signals': alternative_signals,
        'temporal_pattern': temporal_pattern, 'temporal_signal': temporal_signal, 'before_avg': before_avg,
        'after_avg': after_avg, 'glucose_change': glucose_change, 'latest_hba1c': latest_hba1c,
        'previous_hba1c': previous_hba1c, 'hba1c_change': hba1c_change, 'timeline': timeline, 'activity': activity,
        'glucose_labels': glucose_labels, 'glucose_values': glucose_values, 'refill_labels': refill_labels, 'refill_values': refill_values,
        'last_updated': pe['Timestamp'].max().strftime('%d %b %Y, %I:%M %p'),
    }


def patient_directory():
    _, _, _, info, _ = load_data()
    rows = []
    for _, p in info.iterrows():
        data = analyse_patient(str(p['Patient_ID']))
        rows.append({
            'patient_id': data['patient_id'], 'name': data['name'], 'age': data['age'], 'gender': data['gender'],
            'diabetes_type': data['diabetes_type'], 'medication': data['medication'], 'state': data['state'],
            'state_class': data['state_class'], 'last_updated': data['last_updated']
        })
    order = {'concern':0,'watch':1,'monitor':2,'stable':3}
    rows.sort(key=lambda x: (order.get(x['state_class'], 9), x['patient_id']))
    return rows


@app.route('/')
def index():
    return render_template('index.html', patients=patient_directory())


@app.route('/patients')
def patients():
    return render_template('patients.html', patients=patient_directory())


@app.route('/patient/<patient_id>')
def patient_dashboard(patient_id):
    data = analyse_patient(patient_id)
    if data is None:
        return redirect(url_for('patients'))
    directory = patient_directory()
    return render_template('patient_dashboard.html', **data, patients=directory)


@app.route('/patient/<patient_id>/run-monitoring')
def run_monitoring(patient_id):
    data = analyse_patient(patient_id)
    if data is None:
        return redirect(url_for('patients'))
    events = pd.read_excel(DATA_FILE, sheet_name='Patient_Events')
    events['Timestamp'] = pd.to_datetime(events['Timestamp'])
    patient_events = events[events['Patient_ID'].astype(str) == str(patient_id)]
    existing_ids = set(events['Event_ID'].astype(str))
    n = len(events) + 1
    new_id = f'E{n:03d}'
    while new_id in existing_ids:
        n += 1
        new_id = f'E{n:03d}'
    new_timestamp = patient_events['Timestamp'].max() + pd.Timedelta(hours=1)
    current_glucose = float(patient_events[patient_events['Event_Type']=='GLUCOSE'].sort_values('Timestamp').iloc[-1]['Value'])
    baseline = data['normal_glucose']
    # A small deterministic incoming reading keeps the interaction reproducible.
    if data['state_class'] == 'concern':
        new_value = current_glucose + 3
    elif current_glucose > baseline:
        new_value = current_glucose + 1
    else:
        new_value = current_glucose + 2
    new_event = pd.DataFrame({'Event_ID':[new_id], 'Patient_ID':[str(patient_id)], 'Timestamp':[new_timestamp],
                                      'Event_Type':['GLUCOSE'], 'Value':[new_value], 'Unit':['mg/dL']})
    events = pd.concat([events, new_event], ignore_index=True)
    with pd.ExcelWriter(DATA_FILE, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        events.to_excel(writer, sheet_name='Patient_Events', index=False)
    return redirect(url_for('patient_dashboard', patient_id=patient_id))


if __name__ == '__main__':
    app.run(debug=True)
