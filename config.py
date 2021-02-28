from json import load
from urllib.parse import urljoin

with open("config.json", "r") as f:
    config_dict = load(f)

# Extend configurations by some frequently used values
config_dict["category_url"] = urljoin(config_dict["api_url"], config_dict["category_endpoint"])
config_dict["manufacturer_url"] = urljoin(config_dict["api_url"], config_dict["manufacturer_endpoint"])
