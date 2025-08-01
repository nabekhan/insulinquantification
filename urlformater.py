def timestampvariable(type):
    if type == "treatments":
        entrydatevariable = "created_at"
    elif type == "profiles":
        entrydatevariable = "startDate"
    else:
        raise ValueError("Inappropriate type entered!")

    return entrydatevariable

def urlformater(ptID: str, type: str, startDate, endDate):
    timestamp = timestampvariable(type)
    url = "https://" + ptID +".cgm.bcdiabetes.ca/"
    apiURL = url + "api/v1/" + type + ".json?find[" + timestamp + "][$gte]=" + str(startDate) + "&find[" + timestamp + "][$lte]=" + str(endDate) + "&count=" + str(1000)
    return apiURL