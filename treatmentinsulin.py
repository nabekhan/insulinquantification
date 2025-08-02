from dataretriever import *
from datetime import timezone
# CHECK IF SUSPEND PUMP EVENT SHOWS ENDPOINT IN NS (RESUSPEND?). Check if we are missing any
# variables
def treatmenttimes(treatments):
    tempprofile = {}
    boluscount = {}
    for n in treatments:
        if n["eventType"] == "Temp Basal":
            date = datetime.fromisoformat(timeclean(n["created_at"]))
            rate = n["rate"]
            duration = n["duration"]
            tempprofile[date.replace(tzinfo=timezone.utc)] = {"rate": rate, "duration": duration}
        elif n["eventType"] == "Suspend Pump":
            date = datetime.fromisoformat(timeclean(n["created_at"]))
            rate = 0
            duration = 30  # no duration provided
            tempprofile[date.replace(tzinfo=timezone.utc)] = {"rate": rate, "duration": duration}
        elif float(n["insulin"] or 0) > 0:
            date = datetime.fromisoformat(timeclean(n["created_at"]))
            insulin = n["insulin"]
            boluscount[date.replace(tzinfo=timezone.utc)] = insulin
    return [tempprofile, boluscount]


def treatmentinsulin(nsid, startdate, enddate):
    outputdata = dataFetcher(nsid, "treatments", startdate, enddate)
    #[print(n) for n in outputdata]
    tempdic, bolusdic = treatmenttimes(outputdata)
    #print(tempdic, bolusdic)
    return tempdic, bolusdic
