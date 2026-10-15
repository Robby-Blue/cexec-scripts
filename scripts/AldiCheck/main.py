"""
Adli API Architecture Explanation
 1. The main site, at `https://www.aldi-nord.de/prospekte/aldi-aktuell.html`,
    contains the url to the current leaflet.
 2. The leaflets props contain corresponding `enrichments`-API urls. These
    `enrichments` refer to the leaflets annotations; including those which
    show product pop ups. 
 3. We can filter out the products and get their product ids. The name field can't
    be trusted. We can then use the product ids and another API (the one used for
    the popup when clicked on a product) to get more infos about said products,
    like price, original price, discounts, etc.
"""

import os
import sys
import json
import requests

from datetime import datetime, timedelta

today = datetime.now()
monday = (today - timedelta(days=today.weekday())).replace(hour=10, minute=0, second=0, microsecond=0)
thursday = monday + timedelta(days=3)

MONDAY_UNIX = int(monday.timestamp())
THURSDAY_UNIX = int(thursday.timestamp())

print(f"{monday=}, {MONDAY_UNIX}")
print(f"{thursday=}, {THURSDAY_UNIX}")

TARGET_WORDS_IN_NAME = [
    "sandwichtoast",
    "müsli",
    "milch",
    "landmilch",
    "weidemilch",
    "joghurt"
]

SKIPPED_NAMES = [
    "Joghurt auf Frucht"
]

TARGET_CATEGORIES = [
    "brot-toast",
    "milch-milchgetraenke",
    "joghurt-quark-milchdesserts"
]

def get_data():
    leaflet_url = parse_aldi_page()
    
    enrichment_url, leaflet_name = parse_viewer_page(leaflet_url)
    ids = parse_enrichments(enrichment_url)
    products, raw_products = parse_products(ids)
    target_products = filter_target_products(products)
    return {
        "processed": {
            "found_target_products_info": target_products,
            "all_products_info": products,
        },
        "archival": {
            "current_time": int(today.timestamp()),
            "leaflet_name": leaflet_name,
            "raw_products": raw_products
        }
    }
 
def parse_aldi_page():
    """
    Implement step 1. The url can be found in the page props.
    """
    r = requests.get("https://www.aldi-nord.de/prospekte/aldi-aktuell.html")
    html = r.text
 
    print(f"{r.status_code=}")
    
    start_text = "<script id=\"__NEXT_DATA__\" type=\"application/json\">"
    start_index = html.index(start_text) + len(start_text)
    
    end_text = "</script>"
    end_index = html.index(end_text, start_index)
    
    json_str = html[start_index:end_index]
    data = json.loads(json_str)
    
    leaflet_url = data["props"]["pageProps"]["page"]["link"]
    print(f"{leaflet_url=}")
    
    return leaflet_url

def parse_viewer_page(leaflet_url):
    """
    Implement step 2. The enrichments are originally split into 15 page chunks,
    but that doesn't actually matter for some reason. We grab the url for the
    first chunk and replace `Page1-15` with `Page1-1000` to get a url to get all
    enrichments in one request.
    """
    
    r = requests.get(leaflet_url)
    print(f"{r.status_code=}")
    html = r.text
 
    start_text = "window.staticSettings ="
    start_index = html.index(start_text) + len(start_text)
    
    end_text = ";window.dataStore"
    end_index = html.index(end_text, start_index)
    
    json_str = html[start_index:end_index]
    
    data = json.loads(json_str)
    
    enrichment_urls = data["enrichments"]["chunkUrls"]
    first_key = list(enrichment_urls.keys())[0]
    
    enrichment_url = enrichment_urls[first_key]
    enrichment_url = enrichment_url.replace(first_key, "1-1000")

    print(f"{enrichment_url=}")
    
    leaflet_name = data["name"]
    print(f"{leaflet_name=}")
    
    return enrichment_url, leaflet_name

def parse_enrichments(enrichments_url):    
    r = requests.get(enrichments_url)
    print(f"{r.status_code=}")
    enrichments = r.json()["enrichments"]
    
    product_ids = []
    for enrichment in enrichments:
        if "productId" not in enrichment:
            continue
        product_ids.append(enrichment["productId"])

    print(f"{len(product_ids)=}")
    return product_ids

def parse_products(product_ids):
    ids_str = ",".join(product_ids)
    r = requests.get(f"https://www.aldi-nord.de/api/product/pds/{ids_str}")
    print(f"{r.status_code=}")

    products_data = r.json()["products"]
    print(f"{len(products_data)=}")
    
    found_unique_products = []
    found_unique_names = []
        
    for product_data in products_data:
        try: # some items are just weird sometimes
            product_info = get_product_info(product_data)
        except Exception as e:
            id = product_data["objectID"]
            print(f"Error parsing {id}: {repr(e)}")
            continue
        if not product_info:
            continue

        found_unique_name = product_info["name"]
        if found_unique_name in found_unique_names:
            continue
        found_unique_names.append(found_unique_name)
        
        found_unique_products.append(product_info)
            
    print(f"{len(found_unique_products)=}")
    
    return found_unique_products, products_data

def filter_target_products(products):        
    found_target_products = [
        product for product in products
        if product["is_target_product"] and product["is_on_sale"]
    ]
    print(f"{len(found_target_products)=}")
    
    return found_target_products

def get_product_info(product_data):
    if "currentPrice" not in product_data:
        return None
    
    id = product_data["objectID"]
    name = product_data["name"]
    
    price_field = product_data["currentPrice"]
    
    if "strikePrice" in price_field:
        original_price = price_field["strikePrice"]["strikePriceValue"]
    else:
        original_price = price_field["priceValue"]
    
    promotion_start_ts = price_field["validFrom"]
    promotion_end_ts = price_field["validUntil"]      
    monday_promotion_valid = promotion_start_ts < MONDAY_UNIX < promotion_end_ts
    thursday_promotion_valid = promotion_start_ts < THURSDAY_UNIX < promotion_end_ts 
    
    promotion_valid = monday_promotion_valid or thursday_promotion_valid
    
    if promotion_valid or "strikePrice" not in price_field:
        price = price_field["priceValue"]
    else:
        price = price_field["strikePrice"]["strikePriceValue"]
    
    sale_euro = original_price - price
    sale_percentage = sale_euro / original_price * 100
    is_on_sale_this_week = price != original_price
    is_target_product = check_is_target_product(product_data)
    
    return {
        "id": id,
        "name": name,
        "is_on_sale": is_on_sale_this_week,
        "is_target_product": is_target_product,
        "sale": {
            "price": price,
            "original_price": original_price,
            "sale_percentage": round(sale_percentage),
            "is_on_monday": monday_promotion_valid,
            "is_on_thursday": thursday_promotion_valid
        }
    }

def check_is_target_product(product_data):
    name = product_data["name"]
    categories = product_data["categoryIDs"]

    if name in SKIPPED_NAMES:
        return False
    
    for word in TARGET_WORDS_IN_NAME:
        if word in name_to_words(name):
            return True

    for category in TARGET_CATEGORIES:
        if category in categories:
            return True
    return False

def name_to_words(name):
    name = name.lower()
    name = "".join([c if c.isalpha() else " " for c in name])
    
    return name.split(" ")
              
def create_webhook(products):
    def is_on_sale(monday, thursday):
        def f(product):
            sale = product["sale"]
            return sale["is_on_monday"] == monday and \
                sale["is_on_thursday"] == thursday
        return f
    
    general_sales = [product for product in products if is_on_sale(True, True)(product)]
    monday_sales = [product for product in products if is_on_sale(True, False)(product)]
    thursday_sales = [product for product in products if is_on_sale(False, True)(product)]
    
    fields = [
        create_field("Diese Woche", general_sales),
        create_field("Diesen Montag", monday_sales),
        create_field("Diesen Donnerstag", thursday_sales),
    ]
    fields = [field for field in fields if field is not None]
    
    return {
        "title": "Aldi Prospekt",
        "channel": "GUEST",
        "url": "https://www.aldi-nord.de/prospekte/aldi-aktuell.html",
        "embeds": [
            {
                "fields": fields,
            }
        ]
    }
    
def create_field(day, products):
    if len(products) == 0:
        return None
    
    product_strings = [
        create_product_string(product) for product in products
    ]
    return {
        "name": day,
        "value": "\n".join(product_strings),
        "inline": False
    }

def create_product_string(product):
    name = product["name"]
    sale = product["sale"]

    price = sale["price"]
    original_price = sale["original_price"]
    sale_percentage = sale["sale_percentage"]
    
    return f"{name}: {price}€ (~~{original_price}€~~, -{sale_percentage}%)"

data = get_data()
os.makedirs("/app/output/global/Aldi/archive", exist_ok=True)

processed_data = data["processed"]
with open("/app/output/global/Aldi/current_leaflet_data.json", "w") as f:
    json.dump(processed_data, f)

archival_data = data["archival"]
current_unix = int(today.timestamp())
with open(f"/app/output/global/Aldi/archive/leaflet_data_{current_unix}.json", "w") as f:
    json.dump(archival_data, f)

found_target_products = processed_data["found_target_products_info"]
if len(found_target_products) > 0:
    with open("/app/output/output.json", "w") as f:
        json.dump({
            "webhook": create_webhook(found_target_products)
        }, f)

all_valid_products_info = processed_data["all_products_info"]
all_valid_products_count = len(all_valid_products_info)
if all_valid_products_count < 250:
    print(f"Found just {all_valid_products_count} valid products")
    sys.exit(1)