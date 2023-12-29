"""
This script is designed to quantify the amount of insulin used within a selected time period.
It must:
1) Retrieve the profile of the patient for basal rates - done
2) Retrieve the treatments of the patient such as temp basals and boluses - done
3) Sum the boluses and the temp basals appropriately to get the total amount of insulin delivered
    - It must account for potential profile changes within the selected period
    - It must deal with a cancelled temp basal
    - It must do this all with just a start time, end time, and ns url

Approach:
Retrieve all the data and create a dictionary of basals that can be referred to

"""
import urllib.request
import json
import pytz
from datetime import datetime, timedelta

def calculate_insulin_delivery(profile_dict, temp_basal_dict, bolus_dict, start_time, end_time):
    basal_insulin = 0
    bolus_insulin = 0
    current_time = start_time

    # Find the basal rate active at the start time
    active_rate = find_active_rate_at_time(start_time, profile_dict, temp_basal_dict)

    while current_time < end_time:
        # Find the next significant time point
        next_significant_time = min(
            find_next_temp_basal_start(current_time, temp_basal_dict),
            find_next_profile_change(current_time, profile_dict),
            current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
            end_time
        )

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

        while profile_date < next_date: # need to add nextday to profile_date
            for entry in profile_entries:
                # first convert to pt's time zone
                local_time = profile_date.astimezone(timezone)
                # add time
                local_time = local_time.replace(hour = int(entry['time'].split(':')[0]), minute = int(entry['time'].split(':')[1]))
                # convert back to gmt time
                gmt_time = local_time.astimezone(pytz.utc)

                # add the value if it is before the next_date
                # !! need a fix if there is no next_date!!
                if gmt_time < next_date and gmt_time > profile_date:
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

    # example url for retrieving profiles: https://scrappy.cgm.bcdiabetes.ca/api/v1/profiles?find[startDate][$gte]=2023-11-01&find[startDate][$lte]=2023-11-30&count=10000000
    # example url for treatments:          https://scrappy.cgm.bcdiabetes.ca/api/v1/treatments.json?find[created_at][$gte]=2023-11-20&find[created_at][$lte]=2023-11-30&count=10000000


if __name__ == '__main__':
    patient_name = input("Input Patient Name: ")
    if patient_name == "":
        print("Running Trial... Pt Name: Scrappy; Pt URL: https://scrappy.cgm.bcdiabetes.ca/")
        patient_name = "Scrappy"
        ns_url = "https://scrappy.cgm.bcdiabetes.ca/"
        starttime = "2023-12-01"
        endtime = "2023-12-24"
    else:
        ns_url = input("Input Nightscout URL (ex: https://scrappy.cgm.bcdiabetes.ca/): ")
        timezone = input('Input Timezone (valid options are "pst" or "utc"): ')
        starttime = input('Enter your start date and time (ex: 2017-12-31T23:12')
        endtime = input('Enter your start date and time (ex: 2017-12-31T23:22')



    ns = nightscout(patient_name, ns_url)
    profile_dict = nightscout.basalDic(ns, starttime, endtime)
    treatment_dict = nightscout.treatmentDic(ns, starttime, endtime)
    temp_basal_dict = treatment_dict[0]
    bolus_dict = treatment_dict[1]

utc = pytz.utc
pst = pytz.timezone("Canada/Pacific")
start_time = datetime(2023, 12, 19, 8, 12, 0, tzinfo=utc)
end_time = datetime(2023, 12, 20, 8, 12, 0, tzinfo=utc)

insulin_list = calculate_insulin_delivery(profile_dict, temp_basal_dict, bolus_dict, start_time, end_time)
basal_insulin = insulin_list[0]
bolus_insulin = insulin_list[1]
total_insulin = basal_insulin + bolus_insulin

print(f"Total insulin delivered from {start_time} to {end_time}: {total_insulin:.2f} units. Basal: {basal_insulin:.2f} and Bolus: {bolus_insulin:.2f}")