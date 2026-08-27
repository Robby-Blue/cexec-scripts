import json
import requests

def is_released():
    r = requests.get("https://www.geodaten.niedersachsen.de/startseite/datenangebot/open_data_portale/open-data-portale-136000.html")
    html = r.text
    
    is_planned = "ist derzeit in Planung" in html
    
    return not is_planned

def create_webhook():
    return {
        "title": "Open Data Portal Niedersachsen released",
        "url": "https://www.geodaten.niedersachsen.de/startseite/datenangebot/open_data_portale/open-data-portale-136000.html",
        "embeds": [
            {
                "fields": [
                    create_field()
                ],
            }
        ]
    }
    
def create_field():    
    return {
        "name": "Not Planned Anymore",
        "value": "The Open Data Portal Niedersachsen is not \"derzeit in Planung\" anymore, apparently.",
        "inline": False
    }

if is_released():
    with open("/app/output/output.json", "w") as f:
        json.dump({
            "webhook": create_webhook()
        }, f)