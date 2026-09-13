import output_parser
import genanki
import json

styling = """
.card {
    font-family: arial;
    font-size: 20px;
    text-align: center;
    color: black;
    background-color: white;
}
.media {
    maxwidth: 100%;
}
"""

normal_model = genanki.Model(
    1958670534,
    "Normal Model",
    fields=[
        {"name": "Title"},
        {"name": "Solution"}
    ],
    templates=[
        {
            "name": "Card",
            "qfmt": "{{Title}}",
            "afmt": "{{FrontSide}}<hr id=\"answer\">{{Solution}}"
        },
    ],
    css=styling)

data = output_parser.parse_file("anki.txt")
deck_data = data["deck"]

deck_name = deck_data["name"]
print(f"{deck_name=}")

deck = genanki.Deck(
    deck_data["id"],
    deck_name)
package = genanki.Package(deck)

ids = []
front_texts = []

cards = data["cards"]
print(f"{len(cards)=}")

for card_data in cards:
    id = card_data["id"]
    front_text = card_data["topic"] + ": " + card_data["front"]
    
    if id in ids:
        print(f"Duplicate Id: '{id}'")
    ids.append(id)
    if front_text in front_texts:
        print(f"Duplicate Front Text: '{front_text}'")
    front_texts.append(front_text)
    
    note = genanki.Note(
        model=normal_model,
        fields=[front_text, card_data["back"]],
        guid=id,
        tags=[card_data["topic"]])
    deck.add_note(note)

package.write_to_file("output.apkg")

with open("/app/output/output.json", "w") as f:
    json.dump({
        "webhook": {
            "title": f"Created Anki Deck {deck_name}",
            "embeds": [
                {
                    "fields": [
                        {
                            "name": "Stats",
                            "value": f"Cards: {len(cards)}",
                            "inline": False
                        },
                    ],
                }
            ],
            "include_file": {
                "name": "output.apkg",
                "path": "run/output.apkg"
            }
        }
    }, f)