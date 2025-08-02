from dataretriever import *
from datetime import timezone


def glucosedata(data):
    date = timestampvariable("entries")
    # Select dates of glucose readings
    sgv_dates = list([datetime.fromisoformat(timeclean(entry[date])).replace(tzinfo=timezone.utc) for entry in data if 'sgv' in entry])
    # Select all glucose readings
    sgv_values = list([entry['sgv'] for entry in data if 'sgv' in entry])
    # Combine glucose, date readings into list
    sgv_values_dt = {}
    for index, value in enumerate(sgv_values):
        sgv_values_dt[sgv_dates[index]] = value/18.016 # convert to mmol/L
    return sgv_values_dt

def glucosereadings(nsid, startdate, enddate):
    outputdata = dataFetcher(nsid, "entries", startdate, enddate)
    #[print(n) for n in outputdata]
    glucosedic = glucosedata(outputdata)
    #print(glucosedic)
    return glucosedic

