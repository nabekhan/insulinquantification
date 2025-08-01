from dataretriever import *
import pytz

# assumes default profile is being used !!!! MAY NOT WORK WITH MULTIPROFILE IN LOOP/AAPS!!!
def basalprofiles(profiles):
    basalprofile = {}
    timestamp = timestampvariable("profiles")

    for n in profiles:
        date = timeclean(n[timestamp])
        store = n['store']
        # Loop/AAPS capitalize default while trio has it lowercase
        # Find the key in 'store' dict that matches 'default' case-insensitively
        default_key = next((k for k in store if k.lower() == 'default'), None)
        if not default_key:
            print("Could not find default profile")

        basaldic = store[default_key]['basal']
        timezone = store[default_key]['timezone']
        basalprofile[date] = [timezone, basaldic]

    return basalprofile

# Check to confirm the patient's profiles are in their timezones but the start dates are not
def basaltimes(basal_data, enddate):
    # Get the dates of each profile
    listofdates = []
    for profile_date in basal_data:
        listofdates.append(profile_date)
    listofdates.append(str(enddate))
    listofdates = sorted(listofdates)
    # Need to create dictionary of dates/time and values
    basal_dict = {}

    for index, profile_date in enumerate(listofdates[:-1]): # get the index and value for first item. Skip the last item
        # using that first item, we then want to pull it out of the dictionary
        profile_entries = basal_data[profile_date][1] # get the profile associated with that time
        timezone = pytz.timezone(basal_data[profile_date][0]) # get the timezone of the profile
        gmttimezone = pytz.timezone('UTC')
        profile_date = gmttimezone.localize(datetime.fromisoformat(profile_date))
        next_date = gmttimezone.localize(datetime.fromisoformat(listofdates[index + 1]))
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
                if gmt_time < next_date and gmt_time > profileset:
                    basal_dict[gmt_time] = entry['value']

            profile_date = profile_date + timedelta(days=1)

    return basal_dict

def basalinsulin(nsid:str, startdate:str, enddate:str):
    start_anchor = datetime.fromisoformat(startdate)  # earliest point we care about
    cur_end = datetime.fromisoformat(enddate)  # sliding window upper bound

    buffer_days = 3
    max_buffer = 365 * 2 # stop after scanning for 2 years
    ts_key = timestampvariable("profiles")

    output_rows: list[dict] = []

    while True:
        # next window goes back `buffer_days` from cur_end
        cur_start = cur_end - timedelta(days=buffer_days)

        rows = dataFetcher(
            nsid,
            "profiles",
            cur_start.isoformat(timespec="seconds"),
            cur_end.isoformat(timespec="seconds"),
        )

        if rows:  # ✔ got data
            output_rows.extend(rows)

            # stop once we’ve crossed the original anchor
            if datetime.fromisoformat(timeclean(rows[-1][ts_key])) <= start_anchor:
                break

            # slide the window back (avoid overlap by 1 s)
            cur_end = cur_start - timedelta(seconds=1)
            buffer_days = 3  # reset stride
        else:  # empty window
            if buffer_days >= max_buffer:
                raise ValueError("Reached two years with no profile changes!")
            buffer_days *= 2  # widen the net

    #[print(n) for n in output_rows]
    basalrates = basalprofiles(output_rows)
    # [print(date, basal) for date, basal in basalrates.items()]
    basaldict = basaltimes(basalrates, enddate)
    # print(basaldict)
    return basaldict

