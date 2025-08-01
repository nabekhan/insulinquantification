from urlformater import *
import time
from datetime import datetime, timedelta
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import json
from timecleaner import *
from private.examplens import *

def dataFetcher(
        ptID: str,
        type: str,
        startDate: str,
        endDate: str,
        result=None,
        *,
        max_retries: int = 3,
        base_backoff: int = 4,  # 2 s, 4 s, 8 s …
):
    if result is None:
        result = []

    timestamp = timestampvariable(type)
    builtURL = urlformater(ptID, type, startDate, endDate)
    # print(builtURL)
    # print(f"Scanning between {startDate} and {endDate}: {builtURL}")

    for attempt in range(max_retries):
        try:
            with urlopen(builtURL, timeout=60) as resp:
                data = json.load(resp)
            # success ⇒ break the retry‑loop
            break
        except (URLError, HTTPError, TimeoutError) as e:
            if attempt < max_retries - 1:
                wait = base_backoff ** attempt
                print(f"{e} — retrying in {wait}s …")
                time.sleep(wait)
                continue
            else:
                # exhausted retries → re‑raise (or return None / log, etc.)
                raise

    if data:
        result += data
        lastdtstring = timeclean(data[-1][timestamp])
        nexttime = (datetime.fromisoformat(lastdtstring) - timedelta(seconds=1))
        nextendDate = nexttime.isoformat()
        dataFetcher(ptID, type, startDate, nextendDate, result,
                    max_retries=max_retries, base_backoff=base_backoff)
    return result
