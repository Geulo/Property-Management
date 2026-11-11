import os

import requests

# The seam. In Assignment 1 this was `from src.property import get_property`; now it is
# an HTTP call to the property service, found through PROPERTY_URL.


class PropertyServiceUnavailable(Exception):
    pass


def fetch_property(property_id, authorization):
    # Returns the property, None if it does not exist (or is not this user's), and raises
    # PropertyServiceUnavailable if the property service is down, slow or broken.
    base_url = os.environ.get("PROPERTY_URL", "http://property:8000").rstrip("/")
    timeout_s = float(os.environ.get("PROPERTY_TIMEOUT_S", "2"))

    try:
        response = requests.get(
            f"{base_url}/properties/{property_id}",
            headers={"Authorization": authorization},  # pass the user's token on
            timeout=timeout_s,
        )
    except requests.RequestException as error:
        raise PropertyServiceUnavailable(str(error)) from error

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise PropertyServiceUnavailable(f"property service answered {response.status_code}")
    return response.json()
