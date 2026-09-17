import pandas as pd

# ============================================================
# DIABETES ADHERENCE MONITORING SYSTEM
# HOUR 2 — Detection + Explainable Clinician Alert
# ============================================================

file = "diabetes_adherence_data.xlsx"

# ------------------------------------------------------------
# Read Excel sheets
# ------------------------------------------------------------
events = pd.read_excel(file, sheet_name="Patient_Events")
refills = pd.read_excel(file, sheet_name="Refills")
labs = pd.read_excel(file, sheet_name="Lab_Results")
patient = pd.read_excel(file, sheet_name="Patient_Info")
baseline = pd.read_excel(file, sheet_name="Baseline")

# Make sure timestamps/dates are interpreted as dates
events["Timestamp"] = pd.to_datetime(events["Timestamp"])
refills["Expected_Refill_Date"] = pd.to_datetime(refills["Expected_Refill_Date"])
refills["Actual_Refill_Date"] = pd.to_datetime(refills["Actual_Refill_Date"])
labs["Date"] = pd.to_datetime(labs["Date"])

# ------------------------------------------------------------
# Personal baseline
# ------------------------------------------------------------
normal_glucose = baseline.loc[0, "Avg_Glucose"]
normal_steps = baseline.loc[0, "Avg_Steps"]
normal_sleep = baseline.loc[0, "Avg_Sleep"]

# ------------------------------------------------------------
# Latest glucose
# ------------------------------------------------------------
glucose_data = events[events["Event_Type"] == "GLUCOSE"].sort_values("Timestamp")
latest_glucose = glucose_data.iloc[-1]["Value"]
glucose_deviation = latest_glucose - normal_glucose

# ------------------------------------------------------------
# Latest refill + refill trend
# ------------------------------------------------------------
latest_delay = refills.iloc[-1]["Days_Delayed"]
latest_refill_date = refills.iloc[-1]["Actual_Refill_Date"]

if len(refills) >= 2:
    previous_delay = refills.iloc[-2]["Days_Delayed"]

    if latest_delay > previous_delay:
        refill_pattern = "Worsening"
    elif latest_delay == previous_delay:
        refill_pattern = "Stable"
    else:
        refill_pattern = "Improving"
else:
    refill_pattern = "Not enough data"

# ------------------------------------------------------------
# Latest activity
# ------------------------------------------------------------
steps_data = events[events["Event_Type"] == "STEPS"].sort_values("Timestamp")
latest_steps = steps_data.iloc[-1]["Value"]

# ------------------------------------------------------------
# Latest sleep
# ------------------------------------------------------------
sleep_data = events[events["Event_Type"] == "SLEEP"].sort_values("Timestamp")
latest_sleep = sleep_data.iloc[-1]["Value"]

# ------------------------------------------------------------
# Separate adherence evidence from alternative/context evidence
# ------------------------------------------------------------
adherence_signals = 0
alternative_signals = 0

if glucose_deviation > 20:
    adherence_signals += 1

if latest_delay > 0:
    adherence_signals += 1

if latest_steps < normal_steps * 0.8:
    alternative_signals += 1

if latest_sleep < normal_sleep * 0.8:
    alternative_signals += 1

# ------------------------------------------------------------
# Confidence
# ------------------------------------------------------------
if adherence_signals == 2 and alternative_signals == 0:
    confidence = "High"
elif adherence_signals == 2 and alternative_signals >= 1:
    confidence = "Moderate"
else:
    confidence = "Low"

# ------------------------------------------------------------
# Temporal analysis:
# Did glucose worsen after the refill-related boundary?
# ------------------------------------------------------------
before_refill = glucose_data[
    glucose_data["Timestamp"] < latest_refill_date
]

after_refill = glucose_data[
    glucose_data["Timestamp"] >= latest_refill_date
]

if len(before_refill) > 0 and len(after_refill) > 0:
    before_avg = before_refill["Value"].mean()
    after_avg = after_refill["Value"].mean()
    glucose_change = after_avg - before_avg
else:
    before_avg = 0
    after_avg = 0
    glucose_change = 0

# Prototype rule — not a medical threshold
if glucose_change > 10:
    temporal_pattern = "Worsening after refill disruption"
else:
    temporal_pattern = "No clear worsening pattern"

# Temporal evidence signals
temporal_signal = 0

if glucose_change > 10:
    temporal_signal = 1

if latest_delay > 0:
    temporal_signal += 1

# ------------------------------------------------------------
# Final adherence assessment
# ------------------------------------------------------------
if (
    adherence_signals == 2
    and refill_pattern == "Worsening"
    and temporal_signal == 2
):
    final_state = "POSSIBLE ADHERENCE CONCERN"
elif adherence_signals == 2:
    final_state = "WATCH"
elif adherence_signals == 1:
    final_state = "MONITOR"
else:
    final_state = "STABLE"

# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------
print("\n--- PATIENT INFORMATION ---")
print("Patient ID:", patient.loc[0, "Patient_ID"])
print("Diabetes Type:", patient.loc[0, "Diabetes_Type"])
print("Medication:", patient.loc[0, "Medication"])

print("\n--- BASELINE ---")
print("Normal glucose:", normal_glucose, "mg/dL")
print("Normal steps:", normal_steps)
print("Normal sleep:", normal_sleep, "hours")

print("\n--- CURRENT SIGNALS ---")
print("Latest glucose:", latest_glucose, "mg/dL")
print("Glucose deviation:", glucose_deviation, "mg/dL")
print("Latest refill delay:", latest_delay, "days")
print("Latest steps:", latest_steps)
print("Latest sleep:", latest_sleep, "hours")

print("\n--- EVIDENCE ANALYSIS ---")
print("Adherence-related signals:", adherence_signals)
print("Alternative/context signals:", alternative_signals)
print("Confidence:", confidence)

print("\n--- REFILL TREND ---")
print("Refill pattern:", refill_pattern)

print("\n--- TEMPORAL ANALYSIS ---")
print("Average glucose before refill:", round(before_avg, 1), "mg/dL")
print("Average glucose after refill:", round(after_avg, 1), "mg/dL")
print("Glucose change:", round(glucose_change, 1), "mg/dL")
print("Temporal pattern:", temporal_pattern)
print("Temporal evidence signals:", temporal_signal, "/2")

print("\n--- FINAL ASSESSMENT ---")
print("Final state:", final_state)
print("Confidence:", confidence)

# ------------------------------------------------------------
# Clinician alert
# ------------------------------------------------------------
print("\n--- CLINICIAN ALERT ---")

if final_state == "POSSIBLE ADHERENCE CONCERN":
    print("ALERT: Possible medication adherence concern")
    print("Confidence:", confidence)
    print("Evidence:")
    print("- Glucose is above personal baseline")
    print("- Recent refill was delayed")
    print("- Refill delay pattern is worsening")
    print("- Glucose worsened across the refill-related time boundary")
    print("Alternative/context:")
    print("- Activity and/or sleep also changed")
    print("Action: Review the patient's treatment and adherence context.")
else:
    print("No strong clinician alert generated.")

# ------------------------------------------------------------
# Save alert without deleting previous alerts
# ------------------------------------------------------------
if final_state == "POSSIBLE ADHERENCE CONCERN":
    try:
        old_alerts = pd.read_excel(file, sheet_name="Alerts")
    except Exception:
        old_alerts = pd.DataFrame(
            columns=[
                "Alert_ID",
                "Patient_ID",
                "Date",
                "State",
                "Confidence",
                "Reason",
            ]
        )

    # Prevent duplicate Alert IDs
    alert_number = len(old_alerts) + 1

    new_alert = pd.DataFrame({
        "Alert_ID": [f"A{alert_number:03d}"],
        "Patient_ID": [patient.loc[0, "Patient_ID"]],
        "Date": [pd.Timestamp.now().date()],
        "State": [final_state],
        "Confidence": [confidence],
        "Reason": [
            "Glucose above baseline + refill delay + worsening refill trend "
            "+ temporal worsening after refill disruption"
        ],
    })

    all_alerts = pd.concat([old_alerts, new_alert], ignore_index=True)

    with pd.ExcelWriter(
        file,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace",
    ) as writer:
        all_alerts.to_excel(
            writer,
            sheet_name="Alerts",
            index=False,
        )

    print("\nNew alert added to Alerts sheet.")
