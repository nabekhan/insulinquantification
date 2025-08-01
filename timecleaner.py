# Removes decimals and timezone from time.
def timeclean(date: str):
    return date.rsplit('.', 1)[0].replace("Z", "")