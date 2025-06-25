#!/usr/bin/env python3
"""
MuleSoft Anypoint Exchange Documentation Extractor

This script extracts documentation from MuleSoft Anypoint Exchange using the Portal APIs.
It downloads portal information, pages, and resources (images) for specified assets.
"""

import os
import sys
import json
import requests
import re
import urllib.parse
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Install with: pip install python-dotenv")
    print("Continuing with system environment variables...")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    print("Continuing with system environment variables...")

try:
    from markdownify import markdownify as md

    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False
    print(" markdownify not available - HTML content will be saved as-is")


def truncate_json_response(response_data: Any, max_length: int = 1000) -> str:
    """Truncate JSON response for logging purposes"""
    try:
        json_str = json.dumps(response_data, indent=2)
        if len(json_str) > max_length:
            return json_str[:max_length] + "... [truncated]"
        return json_str
    except Exception:
        return str(response_data)[:max_length]


def extract_image_info(html_content: str) -> List[Dict[str, str]]:
    """Extract both alt attributes and src URLs from img tags in HTML content"""
    # Pattern to match img tags and capture both src and alt attributes
    img_pattern = r'<img[^>]*(?:src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']+)["\']|alt=["\']([^"\']+)["\'][^>]*src=["\']([^"\']+)["\'])[^>]*>'

    images = []
    matches = re.finditer(img_pattern, html_content, re.IGNORECASE)

    for match in matches:
        # Handle both possible orders of src and alt attributes
        if match.group(1) and match.group(2):  # src first, then alt
            src_url = match.group(1)
            alt_text = match.group(2)
        elif match.group(3) and match.group(4):  # alt first, then src
            src_url = match.group(4)
            alt_text = match.group(3)
        else:
            continue

        # Extract resource path from the alt attribute or src URL
        resource_path = alt_text

        # If alt text looks like a path (contains resources/), use it directly
        # Otherwise, try to extract from src URL
        if 'resources/' not in alt_text and src_url:
            # Extract resource path from src URL
            # Example: https://anypoint.mulesoft.com/exchange/.../resources/Screenshot...png
            if '/resources/' in src_url:
                resource_path = src_url.split('/resources/')[-1]
                # URL decode the resource path
                resource_path = urllib.parse.unquote(resource_path)

        images.append({
            'src_url': src_url,
            'alt_text': alt_text,
            'resource_path': resource_path
        })

    return images


class AnypointExchangeClient:
    """Client for interacting with MuleSoft Anypoint Exchange API"""

    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.session = requests.Session()

    def authenticate(self) -> bool:
        """Authenticate with Anypoint Platform using OAuth2 client credentials flow"""
        auth_url = f"{self.base_url}/accounts/api/v2/oauth2/token"

        print(f" Getting access token...")
        print(f" POST {auth_url}")

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = self.session.post(auth_url, data=payload, headers=headers)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()

            auth_data = response.json()
            self.access_token = auth_data.get("access_token")

            if self.access_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                })
                print(" Successfully generated Anypoint Platform access token")
                print(f" Response Body: {truncate_json_response(auth_data)}")
                return True
            else:
                print(" Failed to get access token from response")
                return False

        except requests.exceptions.RequestException as e:
            print(f" Authentication failed: {e}")
            return False

    def get_portal_info(self, org_id: str, asset_id: str, version: str) -> Optional[Dict]:
        """Get portal information for an asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{org_id}/{asset_id}/{version}/portal"

        print(f" Fetching portal info for {org_id}:{asset_id}:{version}")
        print(f" GET {url}")

        try:
            response = self.session.get(url)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()

            portal_data = response.json()
            print(f" Response Body: {truncate_json_response(portal_data)}")
            print(f" Successfully retrieved portal info")
            return portal_data

        except requests.exceptions.RequestException as e:
            print(f" Failed to get portal info for {asset_id}: {e}")
            return None

    def get_portal_pages(self, org_id: str, asset_id: str, version: str) -> Optional[List[Dict]]:
        """Get portal pages for an asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{org_id}/{asset_id}/{version}/portal/pages"

        print(f" Fetching portal pages for {org_id}:{asset_id}:{version}")
        print(f" GET {url}")

        try:
            response = self.session.get(url)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()

            pages_data = response.json()
            print(f" Response Body: {truncate_json_response(pages_data)}")

            pages = pages_data if isinstance(pages_data, list) else pages_data.get('pages', [])
            print(f" Found {len(pages)} portal pages")
            return pages

        except requests.exceptions.RequestException as e:
            print(f" Failed to get portal pages for {asset_id}: {e}")
            return None

    def get_portal_page_content(self, org_id: str, asset_id: str, version: str, page_path: str) -> Optional[Dict]:
        """Get content of a specific portal page using its path"""
        # URL encode the page path to handle spaces and special characters
        encoded_path = urllib.parse.quote(page_path, safe='/')
        url = f"{self.base_url}/exchange/api/v2/assets/{org_id}/{asset_id}/{version}/portal/pages/{encoded_path}"

        print(f" Fetching page content for path: {page_path}")
        print(f" GET {url}")

        try:
            response = self.session.get(url)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()

            # Check content type and handle accordingly
            content_type = response.headers.get('Content-Type', '').lower()

            if 'application/json' in content_type:
                try:
                    page_content = response.json()
                    print(f" Response Body (JSON): {truncate_json_response(page_content)}")
                    print(f" Successfully retrieved page content as JSON")
                    return page_content
                except ValueError as e:
                    print(f" Failed to parse JSON response: {e}")
                    # Fall through to handle as text

            # Handle as text/HTML content
            text_content = response.text
            if text_content.strip():
                # In content replace resources/ with empty string to match downloaded image files
                page_content = {
                    "path": page_path,
                    "content_type": content_type,
                    "content": text_content.replace('resources/', ""),
                    "content_length": len(text_content)
                }
                print(f" Response Body (Text): {text_content[:200]}{'...' if len(text_content) > 200 else ''}")
                print(f" Successfully retrieved page content as text ({len(text_content)} chars)")
                return page_content
            else:
                print(f" Empty response body for page: {page_path}")
                return {
                    "path": page_path,
                    "content_type": content_type,
                    "content": "",
                    "error": "Empty response body"
                }

        except requests.exceptions.RequestException as e:
            print(f" Failed to get page content for path {page_path}: {e}")
            return None

    def get_resource_image(self, group_id: str, asset_id: str, version: str, resource_path: str, new_image_name: str,
                           target_dir: Path = None) -> Optional[bytes]:
        """Fetch image resource using the resources API endpoint"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}/portal/resources/{resource_path}"
        print(f" GET {url}")

        payload = {}
        headers = {
            'Authorization': f"Bearer {self.access_token}",
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request("GET", url, headers=headers, data=payload)
            print(f" Response Status: {response.status_code}")

            if response.status_code == 200:
                if target_dir:
                    # Use the resource path as the filename, preserving the original structure
                    # Remove any leading "resources/" if present since we'll add it to target_dir
                    clean_resource_path = resource_path
                    if clean_resource_path.startswith("resources/"):
                        clean_resource_path = clean_resource_path[10:]  # Remove "resources/" prefix

                    # Create the file path within the target directory
                    file_path = target_dir / new_image_name

                    # Ensure parent directories exist
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(file_path, 'wb') as f:
                        f.write(response.content)

                    print(f" Saved image: {file_path}")

                return response.content
            else:
                print(f" Failed to download image: HTTP {response.status_code}")
                print(f" Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f" Failed to download image {resource_path}: {e}")
            return None


def save_file(content: bytes, file_path: Path) -> bool:
    """Save content to a file"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f" Failed to save file {file_path}: {e}")
        return False


def save_json(data: Dict, file_path: Path) -> bool:
    """Save JSON data to a file"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f" Failed to save JSON file {file_path}: {e}")
        return False


def save_markdown(content: str, file_path: Path) -> bool:
    """Save markdown content to a file"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f" Failed to save markdown file {file_path}: {e}")
        return False


def main():
    """Main function to extract documentation from Anypoint Exchange"""

    start_time = time.time()

    # Get environment variables
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    exchange_url = os.getenv('EXCHANGE_URL', 'https://anypoint.mulesoft.com')
    org_id = os.getenv('ORGANIZATION_ID')
    asset_id = os.getenv('ASSET_ID', 'openapi')
    asset_version = os.getenv('ASSET_VERSION', '1.0.0')
    output_dir = os.getenv('OUTPUT_DIR', 'documentation-export')

    # Validate required environment variables
    if not client_id:
        print(" Error: CLIENT_ID environment variable is required")
        sys.exit(1)

    if not client_secret:
        print(" Error: CLIENT_SECRET environment variable is required")
        sys.exit(1)

    if not org_id:
        print(" Error: ORGANIZATION_ID environment variable is required")
        sys.exit(1)

    print(f" Starting MuleSoft Anypoint Exchange documentation extraction...")
    print(f" Output directory: {output_dir}")
    print(f" Organization ID: {org_id}")
    print(f" Asset ID: {asset_id}")
    print(f" Asset Version: {asset_version}")
    print(f" Exchange URL: {exchange_url}")
    print("=" * 60)

    # Initialize client and authenticate
    client = AnypointExchangeClient(exchange_url, client_id, client_secret)

    if not client.authenticate():
        print(" Failed to authenticate with Anypoint Platform")
        sys.exit(1)

    print("=" * 60)

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f" Created output directory: {output_path.absolute()}")

    # Create documentation and images directories
    documentation_dir = output_path / "documentation"
    images_dir = documentation_dir / "images"
    documentation_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    print(f" Created documentation directory: {documentation_dir.absolute()}")
    print(f" Created images directory: {images_dir.absolute()}")

    docs_downloaded_count = 0

    print("=" * 60)
    print(f" Processing asset: {asset_id}:{asset_version}")

    # Create asset directory
    asset_dir = output_path / f"{asset_id}_{asset_version}"
    asset_dir.mkdir(parents=True, exist_ok=True)

    # Get portal information
    print(f" Downloading documentation for {asset_id}...")
    portal_info = client.get_portal_info(org_id, asset_id, asset_version)
    if portal_info:
        portal_file = asset_dir / "portal_info.json"
        save_json(portal_info, portal_file)
        print(f" Saved portal info: {portal_file}")
        docs_downloaded_count += 1

    # Get portal pages
    portal_pages = client.get_portal_pages(org_id, asset_id, asset_version)
    if portal_pages:
        pages_file = asset_dir / "portal_pages.json"
        save_json(portal_pages, pages_file)
        print(f" Saved portal pages: {pages_file}")

        # Save individual pages as separate files for easier access
        pages_dir = documentation_dir / f"{asset_id}_{asset_version}"
        pages_dir.mkdir(parents=True, exist_ok=True)

        for idx, page in enumerate(portal_pages):
            page_title = page.get('title', f'page_{idx}')
            # Sanitize filename
            safe_title = "".join(c for c in page_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')
            page_file = pages_dir / f"{safe_title}.json"
            save_json(page, page_file)
            print(f" Saved page: {page_file}")

        docs_downloaded_count += len(portal_pages)

        # Download actual page content using the path field
        for idx, page in enumerate(portal_pages):
            page_path = page.get('path')
            page_name = page.get('name', f'page_{idx}')

            if not page_path:
                print(f" No path found for page: {page_name}")
                continue

            # Get filename from path - use part after last slash if present
            # Example: {"path": "9uv-lqc/Content Paged" -> "Content Paged"}
            if '/' in page_path:
                filename = page_path.split('/')[-1]
            else:
                filename = page_path

            # Sanitize filename
            safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            safe_filename = safe_filename.replace(' ', '_')

            # Create a clean name for markdown file (preserve original spacing)
            markdown_name = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()

            # Download the actual page content
            page_content = client.get_portal_page_content(org_id, asset_id, asset_version, page_path)
            if page_content:
                content_file = pages_dir / f"{safe_filename}_content.json"
                save_json(page_content, content_file)
                print(f" Saved page content: {content_file}")
                docs_downloaded_count += 1

                if MARKDOWNIFY_AVAILABLE and 'content' in page_content and page_content.get('content_type','').startswith('text/html'):
                    # Extract image alt attributes before converting to markdown
                    html_content = page_content['content']
                    images = extract_image_info(html_content)
                    image_src_path = ""
                    new_image_name = ""

                    if images:
                        print(f" Found {len(images)} images in page content")


                        # Debug: Print image details
                        for i, image in enumerate(images):
                            print(f"   Image {i + 1}: alt='{image['alt_text']}', resource_path='{image['resource_path']}'")
                            image_src_path = image['src_url']
                            print(f"image_src_path: {image_src_path}")

                        # Fetch each image using the resources API
                        for img_idx, image in enumerate(images):
                            encoded_resource_path = image['resource_path'].replace("resources/", "")
                            print(f" Fetching image: {encoded_resource_path}")
                            print(
                                f"   Using API: /exchange/api/v2/assets/{org_id}/{asset_id}/{asset_version}/portal/resources/{encoded_resource_path}")
                            new_image_name = f"image_{img_idx}.png"
                            image_content = client.get_resource_image(org_id, asset_id, asset_version, f"{encoded_resource_path}", new_image_name, target_dir=images_dir)

                            # Replace image url with local image path
                            if image_src_path in page_content['content']:
                                page_content['content'] = page_content['content'].replace(f"{image_src_path}", f"images/{new_image_name}")

                            if image_content:
                                docs_downloaded_count += 1
                            else:
                                print(f" Failed to fetch image: {image['resource_path']}")

                    # Keep Same markdown file name to match title
                    markdown_file = documentation_dir / f"{markdown_name}.md"
                    markdown_content = md(page_content['content'])
                    save_markdown(markdown_content, markdown_file)
                    print(f" Saved page content as Markdown: {markdown_file}")
                    docs_downloaded_count += 1

            # Add small delay to avoid rate limiting
            time.sleep(0.1)

    # Create summary file
    summary = {
        "extraction_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "asset_id": asset_id,
        "asset_version": asset_version,
        "organization_id": org_id,
        "docs_downloaded": docs_downloaded_count,
        "output_directory": str(output_path),
        "duration_seconds": round(time.time() - start_time, 2)
    }

    summary_file = output_path / "extraction_summary.json"
    save_json(summary, summary_file)

    print("\n" + "=" * 60)
    print(" EXTRACTION SUMMARY")
    print("=" * 60)
    print(f" Duration: {summary['duration_seconds']} seconds")
    print(f" Asset: {asset_id}:{asset_version}")
    print(f" Organization: {org_id}")
    print(f" Documentation items downloaded: {summary['docs_downloaded']}")
    print(f" Output directory: {summary['output_directory']}")
    print(f" Summary saved: {summary_file}")

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"\n Documentation extraction completed in {elapsed_time:.2f} seconds!")
    print(f" Documentation items downloaded: {docs_downloaded_count}")


if __name__ == "__main__":
    main()
