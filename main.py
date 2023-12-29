from pickle import FALSE
# @title Code Snip It

"""
This script is designed to quantify the amount of insulin delivered within a selected time period.

"""
import urllib.request
import json
import pytz
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import numpy as np
def calculate_insulin_delivery(profile_dict, temp_basal_dict, bolus_dict, start_time, end_time):
    basal_insulin = 0
    bolus_insulin = 0
    current_time = start_time

    # Find the basal rate active at the start time
    active_rate = find_active_rate_at_time(start_time, profile_dict, temp_basal_dict)

    while current_time < end_time:
        # Find the next significant time point
        next_temp_basal_end = find_temp_basal_duration(current_time, temp_basal_dict)
        next_temp_basal_start = find_next_temp_basal_start(current_time, temp_basal_dict)
        next_profile_change = find_next_profile_change(current_time, profile_dict)
        next_hour = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        next_significant_time = min(
            next_temp_basal_end,
            next_temp_basal_start,
            next_profile_change,
            next_hour,
            end_time
        ) # issue is if the temp basal ends by itself, the system assumes it last 1 hour at least
        test = active_rate * ((next_significant_time - current_time).total_seconds() / 3600)
        basal_insulin += active_rate * ((next_significant_time - current_time).total_seconds() / 3600)
        # Update the active rate based on what's next
        current_time = next_significant_time
        active_rate = find_active_rate_at_time(current_time, profile_dict, temp_basal_dict)

    # Add bolus doses within the time period
    for bolus_time, bolus_amount in bolus_dict.items():
        if start_time <= bolus_time < end_time:
            bolus_insulin += bolus_amount

    return [basal_insulin, bolus_insulin]

def find_active_rate_at_time(current_time, profile_dict, temp_basal_dict):
    temp_basal = find_active_temp_basal(current_time, temp_basal_dict)
    if temp_basal:
        return temp_basal[0]  # Return the rate of the active temp basal
    else:
        return find_profile_rate(current_time, profile_dict)  # Return the profile rate

def find_next_temp_basal_start(current_time, temp_basal_dict):
    future_starts = [start_time for start_time in temp_basal_dict if start_time > current_time]
    return min(future_starts, default=datetime.max.replace(tzinfo=current_time.tzinfo))

def find_temp_basal_duration(current_time, temp_basal_dict):
    for start_time, details in temp_basal_dict.items():
        end_time = start_time + timedelta(minutes=details['duration'])
        if start_time <= current_time < end_time:
            # Current time is within a temp basal period, return its end time
            return end_time
    # No active temp basal, return a distant future time
    return datetime.max.replace(tzinfo=current_time.tzinfo)

def find_next_profile_change(current_time, profile_dict):
    future_changes = [time for time in profile_dict if time > current_time]
    return min(future_changes, default=datetime.max.replace(tzinfo=current_time.tzinfo))

def find_active_temp_basal(current_time, temp_basal_dict):
    for start_time, details in sorted(temp_basal_dict.items(), reverse=True):
        end_time = start_time + timedelta(minutes=details['duration'])
        if start_time <= current_time < end_time:
            return details['rate'], end_time
    return None

def find_profile_rate(current_time, profile_dict):
    current_rate = None
    for time, rate in sorted(profile_dict.items(), reverse=True):
        if time <= current_time:
            current_rate = rate
            break
    return current_rate
def parse_basal_profile(basal_data):
    # Get the dates of each profile
    listofdates = []
    for profile_date in basal_data:
        listofdates.append(profile_date)
    listofdates.append(str(datetime.utcnow().isoformat()).split(".")[0] + "Z")
    listofdates = sorted(listofdates)
    # Need to create dictionary of dates/time and values
    basal_dict = {}

    for index, profile_date in enumerate(listofdates[:-1]): # get the index and value for first item. Skip the last item
        # using that first item, we then want to pull it out of the dictionary
        profile_entries = basal_data[profile_date][1] # get the profile associated with that time
        timezone = pytz.timezone(basal_data[profile_date][0]) # get the timezone of the profile
        gmttimezone = pytz.timezone('UTC')
        profile_date = gmttimezone.localize(datetime.fromisoformat(profile_date[:-1]))
        next_date = gmttimezone.localize(datetime.fromisoformat(listofdates[index + 1][:-1]))
        profileset = profile_date
        while profile_date - timedelta(days=1) < next_date: # need to add nextday to profile_date
            for entry in profile_entries:
                # first convert to pt's time zone
                local_time = profile_date.astimezone(timezone)
                # add time
                local_time = local_time.replace(hour = int(entry['time'].split(':')[0]), minute = int(entry['time'].split(':')[1]))
                # convert back to gmt time
                gmt_time = local_time.astimezone(pytz.utc)
                # add the value if it is before the next_date
                # !! need a fix if there is no next_date!!
                if gmt_time < next_date and gmt_time > profileset:
                    basal_dict[gmt_time] = entry['value']

            profile_date = profile_date + timedelta(days=1)

    return basal_dict

def retrievebasaldata(URL):
    with urllib.request.urlopen(URL) as url:
        file = json.load(url)
        basalprofile = {}
        for n in range(len(file)):
            date = file[n]['startDate']
            basaldic = file[n]['store'][file[n]['defaultProfile']]['basal'] # get basal rates of profile 0
            timezone = file[n]['store'][file[n]['defaultProfile']]['timezone']
            basalprofile[date] = [timezone, basaldic]
        return parse_basal_profile(basalprofile)

def retrievetreatmentdata(URL):
    with urllib.request.urlopen(URL) as url:
        file = json.load(url)
        tempprofile = {}
        boluscount = {}
        # create dictionary of temp basals and boluses
        for n in range(len(file)):
            if file[n]["eventType"] == "Temp Basal":
                date = datetime.fromisoformat(file[n]["created_at"])
                rate = file[n]["rate"]
                duration = file[n]["duration"]
                tempprofile[date] = {"rate": rate, "duration": duration}
            elif file[n]["eventType"] == "Suspend Pump":
                date = datetime.fromisoformat(file[n]["created_at"])
                rate = 0
                duration = 30 # no duration provided
                tempprofile[date] = {"rate": rate, "duration": duration}
            elif float(file[n]["insulin"] or 0) > 0:
                date = datetime.fromisoformat(file[n]["created_at"])
                insulin = file[n]["insulin"]
                boluscount[date] = insulin
        return [tempprofile, boluscount]

class nightscout:
    def __init__(self, pt, url):
        self.pt= pt
        self.url = url

    def __str__(self):
        return f"{self.pt}: {self.url}"

    def basalDic(self, starttime, endtime):
        profileurl = self.url + "api/v1/profiles?find[startDate][$gte]=" + starttime + "&find[startDate][$lte]=" + endtime + "&count=10000000"
        profile = retrievebasaldata(profileurl)
        return profile

    def treatmentDic(self, starttime, endtime):
        treatmenturl = self.url + "api/v1/treatments.json?find[created_at][$gte]=" + starttime + "&find[created_at][$lte]=" + endtime + "&count=10000000"
        tempbasal = retrievetreatmentdata(treatmenturl)[0]
        bolus = retrievetreatmentdata(treatmenturl)[1]
        return [tempbasal, bolus]

def parseinputdatetime(str):
    date = str.split("t")[0]
    time = str.split("t")[1]
    datelist = [int(date.split("-")[0]), int(date.split("-")[1]), int(date.split("-")[2])]
    timelist = [int(time.split(":")[0]), int(time.split(":")[1])]
    return [datelist, timelist]

if __name__ == '__main__':
    with st.form(key='my_form_to_submit'):
        PatientName = st.text_input("Patient Name")
        PatientNSURL = st.text_input("Patient NS URL (ex: https://vanbunbury.cgm.bcdiabetes.ca/)")
        StartDate = st.text_input("Start datetime (ex: 2023-12-02T09:00)")
        EndDate = st.text_input("End datetime (ex: 2023-12-02T09:00)")
        Timezone = st.text_input("Timezone (only PT and UTC are accepted right now)")
        submit_button = st.form_submit_button(label='Submit')

    if submit_button:
        st.write("Thinking . . .")
        patient_name = PatientName.strip()
        utc = pytz.utc
        ns_url = PatientNSURL.strip()
        timezone = Timezone.lower().strip()
        if timezone == "pt":
            settz = pytz.timezone("PST8PDT")
        elif timezone == "utc":
            settz = pytz.utc
        else:
            print("Invalid Timezone!")

        starttimetz = StartDate.lower().strip()
        starttimetz = parseinputdatetime(starttimetz)
        endtimetz = EndDate.lower().strip()
        endtimetz = parseinputdatetime(endtimetz)

        starttimetz = datetime(starttimetz[0][0], starttimetz[0][1], starttimetz[0][2], starttimetz[1][0], starttimetz[1][1], tzinfo=settz)
        endtimetz = datetime(endtimetz[0][0], endtimetz[0][1], endtimetz[0][2], endtimetz[1][0], endtimetz[1][1], tzinfo=settz)

        starttime = starttimetz.astimezone(utc)
        endtime = endtimetz.astimezone(utc)

        ns = nightscout(patient_name, ns_url)
        buffer = 3
        start_time = starttime - timedelta(days=buffer)
        end_time = endtime + timedelta(days=buffer)
        profile_dict = nightscout.basalDic(ns, str(start_time.date()), str(end_time.date()))

        while not profile_dict:
            buffer = buffer + 15
            start_time = start_time - timedelta(days=buffer)
            profile_dict = nightscout.basalDic(ns, str(start_time.date()), str(end_time.date()))

        while sorted(profile_dict.items())[0][0] > starttime:
            buffer = buffer + 15
            start_time = start_time - timedelta(days=buffer)
            profile_dict = nightscout.basalDic(ns, str(start_time.date()), str(end_time.date()))


        treatment_dict = nightscout.treatmentDic(ns, str(start_time.date()), str(end_time.date()))
        temp_basal_dict = treatment_dict[0]
        bolus_dict = treatment_dict[1]

        insulin_list = calculate_insulin_delivery(profile_dict, temp_basal_dict, bolus_dict, starttime, endtime)
        basal_insulin = insulin_list[0]
        bolus_insulin = insulin_list[1]
        total_insulin = basal_insulin + bolus_insulin
        st.write(f"From {starttimetz} to {endtimetz} for {patient_name}:")
        insulin_dic = {"Patient Name": PatientName, 'Basal Insulin (U)': basal_insulin, 'Bolus Insulin (U)': bolus_insulin, 'Total Insulin (U)': total_insulin}
        st.table(pd.DataFrame(insulin_dic, index=[1]))