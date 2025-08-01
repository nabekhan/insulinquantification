"""
This script is designed to quantify the amount of insulin delivered within a selected time period.

"""
#  $ pip install streamlit streamlit-tz tzdata  (tzdata for servers w/o zoneinfo DB)
from basalinsulin import basalinsulin
from treatmentinsulin import treatmentinsulin
import streamlit as st
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo            # stdlib ≥3.9
from streamlit_tz import streamlit_tz    # community component
import streamlit as st
import pandas as pd
from calculator import calculate_insulin_delivery
from datetime import time

def get_default(key, default_val):
    if key not in st.session_state:
        st.session_state[key] = default_val
    return st.session_state[key]


# build a dict of “America/…” zones (+ UTC)
def build_america_timezones() -> dict[str, str]:
    """Return {label: tz_name} for all America/* zones plus UTC."""
    try:                            # Python 3.11+: zoneinfo.available_timezones()
        from zoneinfo import available_timezones
        all_zones = available_timezones()
    except ImportError:             # older versions → fall back to pytz
        import pytz
        all_zones = pytz.all_timezones

    america = sorted(tz for tz in all_zones if tz.startswith("America/"))
    # Label e.g. "New York (America/New_York)"
    tz_dict = {
        f"{tz.split('/')[-1].replace('_', ' ')} ({tz})": tz
        for tz in america
    }
    tz_dict["UTC"] = "UTC"          # keep an explicit UTC option
    return tz_dict

# pick-timezone helper
TIMEZONES = build_america_timezones()

def pick_timezone(detected: str) -> ZoneInfo:
    """Return a ZoneInfo matching the detected zone, letting the user override."""
    default_label = next(
        (lbl for lbl, name in TIMEZONES.items() if name == detected),
        "UTC"
    )
    lbl = st.selectbox("Timezone (override if needed)",
                       TIMEZONES.keys(),
                       index=list(TIMEZONES).index(default_label))
    return ZoneInfo(TIMEZONES[lbl])


if __name__ == "__main__":
    st.set_page_config(page_title="Nightscout Insulin Calculator", page_icon="🕑")
    st.markdown("<h1 style='text-align: center;'>Nightscout Insulin Calculator</h1>", unsafe_allow_html=True)
    # 1.  Detect browser zone and notify the visitor
    detected_tz = (
        streamlit_tz()          # most reliable one-liner
        or st.context.timezone  # Streamlit ≥1.33; sometimes empty on hot-reload
        or "UTC"
    )
    st.info(f"🕑 Your browser appears to be set to **{detected_tz}**.")
    tz = pick_timezone(detected_tz)      # user can keep / override

    # 2.  Collect form data
    with st.form("my_form_to_submit"):
        nsid       = st.text_input("Nightscout ID",
                                     placeholder="099889e3-4db0-524c-be0f-9f627f4c86b6").strip()

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date")
            start_time = st.time_input("Start time",
                                       value=get_default("start_time", time(0, 0)),
                                       key="start_time")
        with col2:
            end_date   = st.date_input("End date")
            end_time = st.time_input("End time",
                                     value=get_default("end_time", time(3, 0)),
                                     key="end_time")

        submitted = st.form_submit_button("Submit")

    # 3.  Build aware datetimes and convert to UTC
    if submitted:
        st.write("Thinking …")
        start_local = datetime.combine(start_date, start_time, tzinfo=tz)
        end_local   = datetime.combine(end_date,   end_time,   tzinfo=tz)

        if end_local <= start_local:
            st.error("End date/time must be after start date/time.")
            st.stop()

        starttime = start_local.astimezone(timezone.utc)
        endtime   = end_local.astimezone(timezone.utc)

        # 4.  Show / use the results
        st.success("Times converted to UTC:")
        st.write("Start (UTC):", starttime.isoformat())
        st.write("End   (UTC):", endtime.isoformat())


        # offset naive times for calculations
        starttime_naive = starttime.replace(tzinfo=None).isoformat(timespec="seconds")
        endtime_naive = endtime.replace(tzinfo=None).isoformat(timespec="seconds")

        # Get basal insulin
        basaldic = basalinsulin(nsid, starttime_naive, endtime_naive)

        # Get treatment insulin

        treatmentdic = treatmentinsulin(nsid, starttime_naive, endtime_naive)
        tempdic = treatmentdic[0]
        bolusdic = treatmentdic[1]

        insulin_list = calculate_insulin_delivery(basaldic, tempdic, bolusdic, starttime, endtime)
        basal_insulin = insulin_list[0]
        bolus_insulin = insulin_list[1]
        total_insulin = basal_insulin + bolus_insulin
        st.write(f"From {start_local} to {end_local}:")
        insulin_dic = {'Basal Insulin (U)': basal_insulin, 'Bolus Insulin (U)': bolus_insulin, 'Total Insulin (U)': total_insulin}
        st.table(pd.DataFrame(insulin_dic, index=[1]))
