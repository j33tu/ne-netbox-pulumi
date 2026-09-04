import os
import requests

# Configuration
NETBOX_URL = os.getenv("NETBOX_SERVER_URL", "https://myas9346.cloud.netboxapp.com").rstrip("/")
API_TOKEN = "nbt_nm0Yrq5CbhBk.fqIWKWYP6WySjYhdgdQBrwfQJrwkAdjn4bRwlvFZ"

if not API_TOKEN:
    raise ValueError("Missing 'NETBOX_DEV_TOKEN' environment variable.")

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Cleanup order is critical due to foreign key constraints in NetBox
DELETE_ENDPOINTS = [
    "/api/ipam/prefixes/",
    "/api/ipam/vlans/",
    "/api/dcim/racks/",
    "/api/dcim/locations/",
    "/api/dcim/sites/",
    "/api/dcim/regions/",
]


def wipe_endpoint(endpoint: str):
    """Deletes all objects retrieved from a NetBox API endpoint."""
    url = f"{NETBOX_URL}{endpoint}"
    print(f"\n[+] Fetching items from: {endpoint}")

    try:
        response = requests.get(url, headers=HEADERS, params={"limit": 1000}, verify=True)
        response.raise_for_status()
        results = response.json().get("results", [])

        if not results:
            print(f"    No objects found in {endpoint}")
            return

        print(f"    Found {len(results)} items to delete.")
        for item in results:
            item_id = item["id"]
            item_name = item.get("name") or item.get("prefix") or item.get("display") or item_id
            delete_url = f"{url}{item_id}/"

            del_resp = requests.delete(delete_url, headers=HEADERS)
            if del_resp.status_code in (200, 204):
                print(f"    - Successfully deleted ID {item_id} ({item_name})")
            else:
                print(f"    - Failed to delete ID {item_id}: {del_resp.status_code} - {del_resp.text}")

    except Exception as e:
        print(f"    [!] Error targeting {endpoint}: {e}")


def main():
    print(f"=== Starting NetBox Cleanup on {NETBOX_URL} ===")
    for endpoint in DELETE_ENDPOINTS:
        wipe_endpoint(endpoint)
    print("\n=== NetBox Cleanup Complete ===")


if __name__ == "__main__":
    main()