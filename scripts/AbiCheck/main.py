import json
import requests

from bs4 import BeautifulSoup

def get_years():
    r = requests.get("https://za-aufgaben.nibis.de/")
    print(f"{r.status_code=}")
    
    html = r.text
    root = BeautifulSoup(html, "html.parser")

    elements_with_years = root.select("[data-jahr]")
    years = set()

    for element in elements_with_years:
        year = element["data-jahr"]
        years.add(year)
    
    years = sorted(years)
    print(f"{years=}")
    return years

def create_webhook(years):
    return {
        "title": "upcoming zdf broadcasts",
        "url": "https://za-aufgaben.nibis.de/",
        "embeds": [
            {
                "fields": [
                    create_field(years)
                ],
            }
        ]
    }
    
def create_field(years):    
    return {
        "name": "za-aufgaben.nibis.de includes 2026 now",
        "value": f"{years=}",
        "inline": False
    }

years = get_years()

is_updated = "2025" in years

if is_updated:
    with open("/app/output/output.json", "w") as f:
        json.dump({
            "webhook": create_webhook(years)
        }, f)