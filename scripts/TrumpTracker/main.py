import json
import requests

def get_data():
    r = requests.get("https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts&exintro&explaintext&titles=Donald_Trump&redirects=true&exintro=true",
        headers={
            "User-Agent": "TrumpTracker"
        })

    print(f"{r.status_code=}")
    
    assert r.status_code == 200
    
    data = r.json()

    pages = data["query"]["pages"]
    page = list(pages.values())[0]

    extract = page["extract"]

    is_index = extract.index("is")
    was_index = extract.index("was")
    print(f"{is_index=}")
    print(f"{was_index=}")
    
    is_dead = was_index < is_index
    print(f"{is_dead=}")
    
    return is_dead, extract
    
def discord_webhook_from_extract(extract):
    return {
        "title": "trump dead",
        "url": "https://en.wikipedia.org/wiki/Donald_Trump",
        "embeds": [
            {
                "fields": [
                    discord_field_from_extract(extract)
                ],
            }
        ]
    }
    
def discord_field_from_extract(extract):    
    extract = extract[:200] + "..."
    return {
        "name": "evidence",
        "value": extract,
        "inline": False
    }

is_dead, extract = get_data()

if is_dead:
    with open("/app/output/output.json", "w") as f:
        json.dump({
            "webhook": discord_webhook_from_extract(extract)
        }, f)