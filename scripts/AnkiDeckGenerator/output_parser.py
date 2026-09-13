import sys

class Reader():
    def __init__(self, txt):
        self.index = 0
        self.src = txt.strip().split("\n")
    
    def expect_section(self, name):
        line = self.read()
        self.expect_eq(f"- {name}", line)

    def expect_subsection(self, name):
        line = self.read()
        self.expect_eq(f"-- {name}", line)
        
    def read_subsection(self, name):
        self.expect_subsection(name)
        return self.read()

    def expect_eq(self, expected, found):
        if expected == found:
            return
        print(f"{self.index}: expected '{expected}', found '{found}'")
        sys.exit(1)
        
    def read(self):
        line = self.src[self.index]
        self.index += 1
        return line
    
    def has_more(self):
        return self.index < len(self.src)

def read_deck(r):
    r.expect_section("Deck")
    name = r.read_subsection("Name")
    id = int(r.read_subsection("Deck ID"))

    return {
        "name": name, 
        "id": id
    }

def read_card(r):
    r.expect_section("New Card")
    id = r.read_subsection("ID")
    topic = r.read_subsection("Topic").replace(" ", "_")
    front = r.read_subsection("Front")
    back = r.read_subsection("Back")

    return {
        "id": id, 
        "topic": topic,
        "front": front,
        "back": back
    }

def parse_file(file_name):
    with open(file_name) as f:
        text = f.read()
        r = Reader(text)

    deck = read_deck(r)
    cards = []
    while r.has_more():
        cards.append(read_card(r))
        
    return {
        "deck": deck,
        "cards": cards
    }