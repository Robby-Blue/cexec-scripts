import json
import csv
import requests
from datetime import datetime, timezone

def get_data():
    r = requests.get("https://www.dashboard-konjunktur.de/api/visualizationdownload/csv/03405e0c-210c-4874-8f41-7d55138db001?newRendering=true")
    print(f"{r.status_code=}")
    
    data_csv = r.text.splitlines()
    print(f"{len(data_csv)=} lines")
        
    data_reader = csv.DictReader(data_csv, delimiter=";")
    data = list(data_reader)
    
    date_now = int(data[-1]["Datum"]) // 1000
    dt = datetime.fromtimestamp(date_now, tz=timezone.utc)
    date_now_formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{date_now=} ({date_now_formatted=})") 
    
    one_year = 60 * 60 * 24 * 365
    
    one_year_ago = date_now - one_year
    two_years_ago = one_year_ago - one_year

    this_year_clean_percent = get_clean_percent_time_frame(one_year_ago, date_now, data)
    last_year_clean_percent = get_clean_percent_time_frame(two_years_ago, one_year_ago, data)
    print(f"{this_year_clean_percent=}")
    print(f"{last_year_clean_percent=}")
    
    growth = round((this_year_clean_percent-last_year_clean_percent) / last_year_clean_percent * 100, 2)
    print(f"{growth=}")

    return {
        "last_date": date_now,
        "this_year_clean_percent": this_year_clean_percent,
        "last_year_clean_percent": last_year_clean_percent,
        "growth": growth
    }

def get_clean_percent_time_frame(start, end, data):
    clean = 0
    total = 0

    for datapoint in data:
        assert len(datapoint.keys()) == 8
            
        date = int(datapoint["Datum"]) // 1000
            
        datapoint_clean = float(datapoint["Windkraft"]) + \
            float(datapoint["Photovoltaik"]) + \
            float(datapoint["Sonstige Erneuerbare"])
                
        datapoint_total = float(datapoint["Insgesamt"])
    
        if date > start and date <= end:
            clean += datapoint_clean
            total += datapoint_total
    
    return round(clean / total * 100, 2)

def create_webhook(data):
    clean_percent = int(data["this_year_clean_percent"] // 5)
    clean_progress_bar = "█" * clean_percent + "░" * (20 - clean_percent)

    return {
        "title": "Clean Energy Data",
        "url": "https://www.dashboard-konjunktur.de/konjunktur/Energie/1751896525912",
        "embeds": [
            {
                "description": clean_progress_bar,
                "fields": create_fields(data)
            }
        ]
    }

def create_fields(data):
    now = datetime.now()
    year = now.year
    month_name = now.strftime('%b')
    
    last_date = data["last_date"]
    this_year_clean_percent = data["this_year_clean_percent"]
    last_year_clean_percent = data["last_year_clean_percent"]
    growth = data["growth"]
    
    return [
        create_field(
            f"{month_name} {year-1} to {month_name} {year}",
            f"{this_year_clean_percent}% clean"),
        create_field(
            f"{month_name} {year-2} to {month_name} {year-1}",
            f"{last_year_clean_percent}% clean"),
        create_field(
            f"Growth",
            f"{growth}% YoY growth"),
        create_field(
            f"Last Date",
            f"<t:{last_date}:D>")
    ]
    
def create_field(title, text):    
    return {
        "name": title,
        "value": text,
        "inline": False
    }

data = get_data()

with open("/app/output/output.json", "w") as f:
    json.dump({
        "webhook": create_webhook(data)
    }, f)