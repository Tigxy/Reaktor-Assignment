import re
import os
import json
import logging
import requests
from enums import Availability, pretty_availability
from config import config_dict
from urllib.parse import urljoin

# Disable console messages when sending requests
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
availability_pattern = r"^<AVAILABILITY>\n  <CODE>200</CODE>\n  <INSTOCKVALUE>(.+)</INSTOCKVALUE>\n</AVAILABILITY>$"


def split_sized_chunks(l, size):
    for i in range(0, len(l), size):
        yield l[i:i + min(len(l), size)]


def payload_to_availability(payload: str):
    match = re.match(availability_pattern, payload)
    # Determine if we found a match
    if match is not None and len(match.regs) == 2:
        if match[1] == "INSTOCK":
            return Availability.IN_STOCK
        if match[1] == "OUTOFSTOCK":
            return Availability.OUT_OF_STOCK
        if match[1] == "LESSTHAN10":
            return Availability.LESS_THAN_10
    return Availability.UNKNOWN


def load_offline_dict(file):
    if not os.path.exists(file):
        return None

    with open(file, "r") as f:
        text = f.read()

    if text is None or len(text) == 0:
        return None

    return json.loads(text)


def get_content_dict(url):
    try:
        result = requests.get(url, timeout=config_dict["request_timeout"])
    except requests.exceptions.ReadTimeout:
        return None

    if result.status_code == 200:
        try:
            return json.loads(result.content.decode("utf-8"))
        except json.decoder.JSONDecodeError:
            # Response might be gibberish that cannot be parsed
            return None
    return None


def get_category(category_name):
    offline_file = os.path.join("offline_resources", "categories", category_name + ".json")
    if config_dict["offline_mode_active"]:
        content = load_offline_dict(offline_file)
    else:
        request_url = urljoin(config_dict["category_url"], category_name)
        content = get_content_dict(request_url)
        if config_dict["store_last_results"]:
            save_data(offline_file, content)
    return {item["id"]: format_category_item(item) for item in content}


def get_manufacturer(manufacturer_name):
    offline_file = os.path.join("offline_resources", "manufacturers", manufacturer_name + ".json")
    if config_dict["offline_mode_active"]:
        content = load_offline_dict(offline_file)
    else:
        request_url = urljoin(config_dict["manufacturer_url"], manufacturer_name)
        content = get_content_dict(request_url)

    # Determine validity
    if content is None \
            or "code" not in content \
            or content["code"] != 200 \
            or "response" not in content \
            or not isinstance(content["response"], list):
        return None

    if config_dict["store_last_results"]:
        save_data(offline_file, content)
    items = content["response"]
    return {item["id"].lower(): payload_to_availability(item["DATAPAYLOAD"]) for item in items}


def save_data(file, data_dict):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    if data_dict is None:
        return
    with open(file, "w") as f:
        json.dump(data_dict, f, indent=4)


def colors_to_string(colors):
    return ", ".join(colors)


def format_category_item(item):
    return {
        "id": item["id"].lower(),
        "name": item["name"],
        "color": colors_to_string(item["color"]),
        "price": item["price"],
        "manufacturer": item["manufacturer"]
    }


def pretty_product_dict(product):
    """
    Generates a dictionary of values that are formatted nicely to display them
    on the actual website
    :param product: The product to make pretty
    :return: A dictionary of nicely formatted values
    """
    return {
        "id": product.id,
        "name": product.name,
        "manufacturer": product.manufacturer.capitalize(),
        "price": product.price,
        "color": product.colors,
        "available": pretty_availability(Availability(product.available)),
    }

