import json
import requests
import xml.etree.ElementTree as ET


def get_articles():
    r = requests.get("https://www.spiegel.de/politik/index.rss")
    
    print(f"{r.status_code=}")
    
    root = ET.fromstring(r.text)
    channel = root.find("channel")
    articles_xml = channel.findall("item")
    
    print(f"{len(articles_xml)=}")
    
    articles = []
    
    for article_xml in articles_xml:
        title = article_xml.find("title").text
        
        description_xml = article_xml.find("description")
        description = description_xml.text if description_xml is not None else ""
        link = article_xml.find("link").text
        
        article = {
            "title": title,
            "description": description,
            "link": link
        }
        
        print(article)
        
        articles.append(article)
    
    return articles
    
def discord_webhook_from_articles(articles):
    return {
        "title": "SpiegelNews",
        "embeds": [
            {
                "fields": [
                    field_from_article(article)
                    for article in articles[:9]
                ]
            }
        ]
    }

def field_from_article(article):
    title = article["title"]
    description = article["description"]
    link = article["link"]
    
    text = f"{description} [[read more]]({link})"
    
    return {
        "name": title,
        "value": text,
        "inline": False
    }

articles = get_articles()

with open("/app/output/output.json", "w") as f:
    json.dump({
        "webhook": discord_webhook_from_articles(articles)
    }, f)