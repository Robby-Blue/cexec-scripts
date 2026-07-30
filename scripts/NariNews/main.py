import json
import requests

def get_changes():
    r = requests.get("https://www.ennaria.com/")

    print(f"{r.status_code=}")
    
    html = r.text

    status_unauth = r.status_code == 401
    has_password = "Password" in html
    is_coming_soon = "coming soon" in html
    has_me_vid = "https://www.youtube.com/watch?v=IQr5d2HLUm4" in html

    print(f"{status_unauth=}")
    print(f"{has_password=}")
    print(f"{is_coming_soon=}")
    print(f"{has_me_vid=}")
    
    changes = []
    
    if not status_unauth:
        changes.append("authed")
    if not has_password:
        changes.append("password")
    if not is_coming_soon:
        changes.append("coming soon")
    if not has_me_vid:
        changes.append("me vid")
    
    return changes
    
def discord_webhook_from_changes(changes):
    return {
        "title": "nari news!!",
        "url": "https://www.ennaria.com/",
        "embeds": [
            {
                "fields": [
                    discord_field_from_changes(changes)
                ],
            }
        ]
    }
    
def discord_field_from_changes(changes):    
    return {
        "name": "evidence",
        "value": f"{changes=}",
        "inline": False
    }

changes = get_changes()

print(f"{len(changes)=}")

if len(changes) != 0:
    with open("/app/output/output.json", "w") as f:
        json.dump({
            "webhook": discord_webhook_from_changes(changes)
        }, f)