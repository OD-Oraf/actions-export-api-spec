import requests
import json
import os
from typing import List, Dict, Any


def format_categories(categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Reorder category fields to show tagKey first, then value"""
    # Reorder using dictionary comprehension
    reordered_data = [
        {"tagKey": item["tagKey"], "value": item["value"]}
        for item in categories
        if isinstance(item, dict) and "tagKey" in item and "value" in item
    ]

    return reordered_data
def modify_categories(categories):
    """Modify category objects by removing displayName and renaming key to tagKey"""
    modified_categories = []

    for category in categories:
        if isinstance(category, dict):
            # Create a copy to avoid modifying original
            modified_category = {k: v for k, v in category.items() if k != "displayName"}

            # Rename key to tagKey
            if "key" in modified_category:
                modified_category["tagKey"] = modified_category.pop("key")

            modified_categories.append(modified_category)
        else:
            # Keep non-dict items as is
            modified_categories.append(category)

    modified_categories = format_categories(modified_categories)

    return modified_categories
def export_categories(access_token: str, org_id: str,asset_id: str, asset_version: str):
    url = f"https://anypoint.mulesoft.com/exchange/api/v2/assets/{org_id}/{asset_id}/asset"
    print(f" GET {url}")

    payload = {}
    headers = {
      'Authorization': f"Bearer {access_token}"
    }

    try:
        response = requests.request("GET", url, headers=headers, data=payload)

        # Check if request was successful
        response.raise_for_status()

        # Convert to JSON
        json_data = response.json()

        # Extract categories with default fallback
        categories = json_data.get("categories", [])

        if categories:
            print("Categories found:", categories)
            modified_categories = modify_categories(categories)

            with open("categories.json", "w") as f:
                json.dump(modified_categories, f, indent=2)

            print("Categories saved to categories.json")
        else:
            print("No categories found")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
    except KeyError as e:
        print(f"Categories field not found: {e}")

def main():
    org_id = "1bb53e2e-0362-40c7-80cc-273290c8d74b"
    asset_id = "openapi"
    asset_version = "1.0.0"
    access_token = "54ba26c1-8c2d-4365-9bc1-cbbf4203b82c"

    export_categories(access_token, org_id, asset_id, asset_version)


if __name__ == "__main__":
    main()
