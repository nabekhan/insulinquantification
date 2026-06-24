import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timezone

# Import your local modules
from basalinsulin import basalinsulin
from treatmentinsulin import treatmentinsulin
from glucosereadings import glucosereadings
from insulincalculator import calculate_insulin_delivery, hourly_insulin_plot
from glucosecalculator import *

# ==========================================
# USER CONFIGURATION (UTC ONLY)
# ==========================================
NSID = "099889e3-4db0-524c-be0f-9f627f4c86b6"
START_UTC = "2026-01-20 00:00"
END_UTC = "2026-01-25 00:00"

# ==========================================

def insulinused():
    print("--- Nightscout Insulin Calculator (UTC Mode) ---")

    # 1. Parse Strings directly to UTC Datetime objects
    dt_format = "%Y-%m-%d %H:%M"
    try:
        starttime_utc = datetime.strptime(START_UTC, dt_format).replace(tzinfo=timezone.utc)
        endtime_utc = datetime.strptime(END_UTC, dt_format).replace(tzinfo=timezone.utc)
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        return

    if endtime_utc <= starttime_utc:
        print("Error: End time must be after start time.")
        return

    print(f"Time Range: {starttime_utc} to {endtime_utc} (UTC)")

    # 2. Create Naive Strings for Data Fetchers (removing +00:00 suffix)
    starttime_naive = starttime_utc.strftime('%Y-%m-%dT%H:%M:%S')
    endtime_naive = endtime_utc.strftime('%Y-%m-%dT%H:%M:%S')

    # 3. Fetch Data
    print("\nFetching Data...")
    basaldic = basalinsulin(NSID, starttime_naive, endtime_naive)
    treatmentdic = treatmentinsulin(NSID, starttime_naive, endtime_naive)
    glucosedic = glucosereadings(NSID, starttime_naive, endtime_naive)

    # Unpack treatments
    tempdic = treatmentdic[0]
    bolusdic = treatmentdic[1]

    # 4. Calculate Stats
    print("Calculating Stats...")
    insulin_list = calculate_insulin_delivery(basaldic, tempdic, bolusdic, starttime_utc, endtime_utc)

    basal_insulin = insulin_list[0]
    bolus_insulin = insulin_list[1]
    total_insulin = basal_insulin + bolus_insulin
    hourly_insulin = insulin_list[2]

    avgglucose = average_glucose(glucosedic, starttime_utc, endtime_utc)

    # 5. Output Results
    insulin_dic = {
        'Basal (U)': [basal_insulin],
        'Bolus (U)': [bolus_insulin],
        'Total (U)': [total_insulin],
        'Avg BG (mM)': [avgglucose]
    }

    df = pd.DataFrame(insulin_dic)
    print("\n" + "=" * 40)
    print(df.to_string(index=False))
    print("=" * 40)

    # 6. Display Plots (Passing UTC as the timezone)
    print("\nDisplaying plots... (Close windows to exit)")

    fig1 = hourly_insulin_plot(hourly_insulin, timezone.utc)
    if fig1:
        plt.figure(fig1.number)
        plt.title("Hourly Insulin (UTC)")
        plt.show()

    fig2 = avg_glucose_plot(glucosedic, starttime_utc, endtime_utc, 30, timezone.utc)
    if fig2:
        plt.figure(fig2.number)
        plt.title("Avg Glucose (UTC)")
        plt.show()

insulinused()