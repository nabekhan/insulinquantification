from datetime import datetime, timedelta

def calculate_insulin_delivery(basalinsulin, tempdic, bolusdic, start_time, end_time):
    basal_insulin = 0
    bolus_insulin = 0
    current_time = start_time

    # Find the basal rate active at the start time
    active_rate = find_active_rate_at_time(start_time, basalinsulin, tempdic)

    while current_time < end_time:
        # Find the next significant time point
        next_temp_basal_end = find_temp_basal_duration(current_time, tempdic)
        next_temp_basal_start = find_next_temp_basal_start(current_time, tempdic)
        next_profile_change = find_next_profile_change(current_time, basalinsulin)
        next_hour = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        next_significant_time = min(
            next_temp_basal_end,
            next_temp_basal_start,
            next_profile_change,
            next_hour,
            end_time
        )
        test = active_rate * ((next_significant_time - current_time).total_seconds() / 3600)
        basal_insulin += active_rate * ((next_significant_time - current_time).total_seconds() / 3600)
        # Update the active rate based on what's next
        current_time = next_significant_time
        active_rate = find_active_rate_at_time(current_time, basalinsulin, tempdic)

    # Add bolus doses within the time period
    for bolus_time, bolus_amount in bolusdic.items():
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