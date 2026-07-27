import json
import requests

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

def find_broadcasts(name, weekday, token):
    data = get_broadcasts_data(token, weekday)
    
    broadcasts = data["data"]["epg"][0]["broadcasts"]
    
    # if theres no broadcasts at all its probably because the
    # backend hates me but i dont want this script to fail silently 
    assert len(broadcasts) > 0
    print(f"{len(broadcasts)=}")
    
    finds = []
    for broadcast in broadcasts:
        title = broadcast["title"]
        print(f"{title=}")
        if title == name:
            finds.append(broadcast)
    
    return finds


def get_broadcasts_data(token, weekday):
    times = strings_at(weekday)
    print(f"{times=}")
    
    var = {
        "filter": {
            "broadcasterIds": ["ZDF"],
            **times
        }
    }
    var_str = json.dumps(var)

    # this hash represents the graphql query, afaik computed with
    # client side js. no easy way to parse it or generate it
    # from scratch; need to hard code
    ext = {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": "e36a71fb3206e75a82a5438737113b221e43daf0363d85f3eeceda288d158821"
        }
    }
    ext_str = json.dumps(ext)

    url = f"https://api.zdf.de/graphql?operationName=getEpg&variables={var_str}&extensions={ext_str}"

    r = requests.get(url, headers={
        "api-auth": f"Bearer {token}",
        "content-type": "application/json"
    })
    
    print(f"{r.status_code=}")
    return r.json()

def get_api_token():
    r = requests.get("https://www.zdf.de/live-tv")

    html = r.text

    key_index = html.index("apiAuthToken") + len("apiAuthToken__")
    start_index = html.index(r"\"", key_index) + len(r"\"")
    end_index = html.index(r"\"", start_index)

    token = html[start_index:end_index]

    return token

def strings_at(weekday):
    today = date.today()
    target_date = today + relativedelta(weekday=weekday)
    end_date = target_date + timedelta(days=1)

    return {
        "from": to_utc_string(target_date),
        "to": to_utc_string(end_date)
    }

def to_utc_string(date):
    local_dt = datetime.combine(date, datetime.min.time(), tzinfo=ZoneInfo("Europe/Berlin"))

    time_utc = local_dt.astimezone(ZoneInfo("UTC"))
    
    formatted_time = time_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return formatted_time
    
def discord_webhook_from_broadcasts(broadcasts):
    return {
        "title": "upcoming zdf broadcasts",
        "embeds": [
            {
                "fields": [
                    discord_field_from_broadcast(broadcast) for broadcast in broadcasts
                ],
            }
        ]
    }
    
def discord_field_from_broadcast(broadcast):
    title = broadcast["title"]
    text = broadcast["text"].replace("<br>", "\n")
    
    start_time_iso = broadcast["effectiveAirtimeBegin"]
    start_time = format_time_from_iso(start_time_iso)
    
    return {
        "name": f"{title} ({start_time})",
        "value": text,
        "inline": False
    }

def format_time_from_iso(iso_time):
    dt = datetime.fromisoformat(iso_time)
    berlin_dt = dt.astimezone(ZoneInfo("Europe/Berlin"))
    
    months = [
        "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
        "August", "September", "Oktober", "November", "Dezember"
    ]
    
    return f"{berlin_dt.day}. {months[berlin_dt.month - 1]} {berlin_dt.year}, {berlin_dt.strftime('%H:%M')}"

token = get_api_token()

finds = []
finds.extend(find_broadcasts("Die Anstalt", 1, token))
finds.extend(find_broadcasts("ZDF Magazin Royale", 4, token))

if len(finds):
    with open("/app/output/output.json", "w") as f:
        json.dump({
            "webhook": discord_webhook_from_broadcasts(finds)
        }, f)