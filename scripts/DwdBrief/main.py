import json
import requests
import math

from datetime import datetime
from zoneinfo import ZoneInfo
import time

SUNNY = ":sunny:"
CLEAR = ":white_sun_small_cloud:"
CLOUD = ":cloud:"
FOG = ":fog:"
RAIN = ":cloud_rain:"
SNOW = ":cloud_snow:"
ICE = ":ice_cube:"
THUNDERSTORM = ":thunder_cloud_rain:"
WIND = ":wind_blowing_face:"

RED_CROSS = ":x:"

SUNRISE = ":sunrise_over_mountains:"
SUNSET = ":city_sunset:"

# icon codes to weather
# based on the mobile apps strings
# found in resources/res/values/strings.xml of any decomp
icons = [
    {
        "ids": [1],
        "name": "sun",
        "emojis": f"{SUNNY}",
        "is_rain": False
    },
    {
        "ids": [2],
        "name": "clear",
        "emojis": f"{CLEAR}",
        "is_rain": False
    },
    {
        "ids": [3],
        "name": "cloudy",
        "emojis": f"{CLOUD}",
        "is_rain": False
    },
    {
        "ids": [4],
        "name": "overcast",
        "emojis": f"{CLOUD} {CLOUD}",
        "is_rain": False
    },
    {
        "ids": [5, 6],
        "name": "fog",
        "emojis": f"{FOG}",
        "is_rain": False
    },
    {
        "ids": [7, 8, 9, 10, 11, 18, 19],
        "name": "rain",
        "emojis": f"{RAIN}",
        "is_rain": True
    },
    {
        "ids": [12, 13, 20, 21],
        "name": "snow and rain",
        "emojis": f"{SNOW} {RAIN}",
        "is_rain": True
    },
    {
        "ids": [14, 15, 16, 22, 23],
        "name": "snow",
        "emojis": f"{SNOW}",
        "is_rain": True
    },
    {
        "ids": [17, 24, 25],
        "name": "hail",
        "emojis": f"{ICE} {RAIN}",
        "is_rain": True
    },
    {
        "ids": [26, 27, 28, 29, 30],
        "name": "thunderstorm",
        "emojis": f"{THUNDERSTORM}",
        "is_rain": True
    },
    {
        "ids": [31],
        "name": "wind",
        "emojis": f"{WIND}",
        "is_rain": False
    },
]

def get_weather():
    # 10338 is the id for the station in Hannover
    # https://www.dwd.de/EN/ourservices/globalclimatedata/stationsverzeichnis.html
    station_id = "10338"

    r = requests.get(f"https://app-prod-ws.warnwetter.de/v30/stationOverviewExtended?stationIds={station_id}")
    print(f"{r.status_code=}")
    
    data = r.json()[station_id]


    forecast = data["forecast1"]
    
    start_time_ms = forecast["start"]
    step_time_ms = forecast["timeStep"]
    
    now_ms = time.time() * 1000
    ms_since_start = now_ms - start_time_ms
    
    current_index = math.floor(ms_since_start / step_time_ms)
    print(f"{current_index=}")
    
    temperature_now = forecast["temperature"][current_index] / 10
    print(f"{temperature_now=}")


    today = datetime.now(ZoneInfo("Europe/Berlin"))
    formatted_date = today.strftime("%Y-%m-%d")
    print(f"{formatted_date=}")
    
    today_day = None
    for day in data["days"]:
        if day["dayDate"] == formatted_date:
            today_day = day
            break
    
    assert today_day is not None
    
    temperature_min = today_day["temperatureMin"] / 10
    temperature_max = today_day["temperatureMax"] / 10
    print(f"{temperature_min=}")
    print(f"{temperature_max=}")
    
    sunshine_minutes = today_day["sunshine"] / 10
    sunshine_hours = round(sunshine_minutes / 60, 1)
    sunrise = math.floor(today_day["sunrise"] / 1000)
    sunset = math.floor(today_day["sunset"] / 1000)
    print(f"{sunshine_hours=}")
    print(f"{sunrise=}")
    print(f"{sunset=}")
    
    
    precipitation_today = today_day["precipitation"]
    has_precipitation_today = precipitation_today > 0
    print(f"{precipitation_today=}")
    print(f"{has_precipitation_today=}")
    
    icon_id = today_day["icon"]
    print(f"{icon_id=}")
    
    found_icon = None
    for icon in icons:
        if icon_id in icon["ids"]:
            found_icon = icon
            break
    
    has_found_icon = found_icon is not None
    print(f"{has_found_icon=}")
    
    if has_found_icon:
        icon_name = found_icon["name"]
        icon_emojis = found_icon["emojis"]
        icon_is_rain = found_icon["is_rain"]
    else:
        icon_name = f"{icon_id=}"
        icon_emojis = RED_CROSS
        icon_is_rain = False

    print(f"{icon_name=}")
    print(f"{icon_emojis=}")
    print(f"{icon_is_rain=}")
    
    return {
        "condition": {
            "name": icon_name,
            "emojis": icon_emojis,
            "icon_is_raining": icon_is_rain,
            "has_precipitation": has_precipitation_today
        },
        "temperature": {
            "now": temperature_now,
            "min": temperature_min,
            "max": temperature_max
        },
        "sun": {
            "hours": sunshine_hours,
            "rise": sunrise,
            "set": sunset
        }
    }
    
def discord_webhook_from_weather(weather):
    condition = weather["condition"]
    temperature = weather["temperature"]
    sun = weather["sun"]
    
    return {
        "title": "dwdWeather",
        "embeds": [
            {
                "description": condition_to_string(condition),
                "fields": [
                    field_from_temperature(temperature),
                    field_from_sun(sun)
                ]
            }
        ]
    }

def condition_to_string(condition):
    name = condition["name"]
    emojis = condition["emojis"]

    string = f"{emojis} {name}"
    
    if not condition["icon_is_raining"] and condition["has_precipitation"]:
        string += f" (with rain {RAIN})"
    
    return string
    
def field_from_temperature(temperature):
    degree_celsius = "°C"
    
    now = str(temperature["now"]) + degree_celsius
    min = str(temperature["min"]) + degree_celsius
    max = str(temperature["max"]) + degree_celsius
    
    text = f"now: {now}\n({min} to {max})"
    
    return field("temperature", text)

def field_from_sun(sun):
    rise = sun["rise"]
    set = sun["set"]
    
    rise_text = f"{SUNRISE}: {format_time(rise)}"
    set_text = f"{SUNSET}: {format_time(set)}"
    
    text = f"{rise_text}\n{set_text}"
    
    return field("sun", text)

def format_time(time):
    return f"<t:{time}:t> (<t:{time}:R>)"

def field(name, value):
    return {
        "name": name,
        "value": value,
        "inline": False
    }

weather = get_weather()

with open("/app/output/output.json", "w") as f:
    json.dump({
        "webhook": discord_webhook_from_weather(weather)
    }, f)