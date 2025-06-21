#!/usr/bin/env python3
"""
MuleSoft Anypoint Exchange API Spec Downloader

This script downloads OpenAPI specifications, documentation, and metadata
from MuleSoft Anypoint Exchange using the Platform API.
"""

import os
import sys
import json
import requests
import yaml
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import time

try:
    from markdownify import markdownify as md
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False
    print(" markdownify not available - HTML content will be saved as-is")


def truncate_json_response(response_data: Any, max_length: int = 1000) -> str:
    """Truncate JSON response for logging purposes"""
    try:
        json_str = json.dumps(response_data, indent=2, ensure_ascii=False)
        if len(json_str) <= max_length:
            return json_str
        else:
            return json_str[:max_length] + f"\n... (truncated, total length: {len(json_str)} chars)"
    except Exception:
        return str(response_data)[:max_length]


def parse_version(version_str: str) -> tuple:
    """Parse version string into tuple for comparison (e.g., '1.2.3' -> (1, 2, 3))"""
    try:
        # Handle semantic versioning (1.2.3) and simple versioning (1.0)
        parts = version_str.split('.')
        return tuple(int(part) for part in parts)
    except (ValueError, AttributeError):
        # If version parsing fails, treat as string for comparison
        return (version_str,)


def get_latest_assets(assets: List[Dict]) -> List[Dict]:
    """Group assets by assetId and return only the latest version of each"""
    asset_groups = {}
    
    print(f" Processing {len(assets)} assets to find latest versions...")
    
    for asset in assets:
        asset_id = asset.get('assetId')
        group_id = asset.get('groupId')
        version = asset.get('version')
        
        if not all([asset_id, group_id, version]):
            print(f" Skipping asset with missing identifiers: {asset}")
            continue
            
        # Create a unique key for each asset (groupId + assetId)
        key = f"{group_id}/{asset_id}"
        
        if key not in asset_groups:
            asset_groups[key] = asset
            print(f" New asset: {key} v{version}")
        else:
            # Compare versions and keep the latest
            current_version = parse_version(asset_groups[key].get('version', '0'))
            new_version = parse_version(version)
            
            if new_version > current_version:
                old_version = asset_groups[key].get('version')
                asset_groups[key] = asset
                print(f" Updated {key}: v{old_version} → v{version}")
            else:
                print(f" Keeping {key}: v{asset_groups[key].get('version')} (skipping v{version})")
    
    latest_assets = list(asset_groups.values())
    print(f" Filtered to {len(latest_assets)} latest versions from {len(assets)} total assets")
    
    # Show final selection
    print("\n Final asset selection (latest versions only):")
    for asset in latest_assets:
        print(f"  • {asset.get('groupId')}/{asset.get('assetId')} v{asset.get('version')}")
    
    return latest_assets


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

        # MuleSoft Anypoint Platform Access Token Endpoint
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
    
    def get_organizations(self) -> List[Dict]:
        """Get list of organizations the user has access to"""
        # MuleSoft Anypoint Platform API endpoint for user profile
        url = f"{self.base_url}/accounts/api/profile"
        
        print(f" Fetching user organizations...")
        print(f" GET {url}")
        
        try:
            response = self.session.get(url)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()
            user_data = response.json()
            print(f" Response Body: {truncate_json_response(user_data)}")
            
            orgs = user_data.get("memberOfOrganizations", [])
            print(f" Found {len(orgs)} organizations")
            return orgs
        except requests.exceptions.RequestException as e:
            print(f" Failed to get organizations: {e}")
            return []
    
    def search_assets(self, org_id: str, group_id: Optional[str] = None, 
                     asset_id: Optional[str] = None) -> List[Dict]:
        """Search for assets in Exchange"""
        url = f"{self.base_url}/exchange/api/v2/assets"
        
        params = {
            "organizationId": org_id,
            "limit": 100
        }
        
        if group_id:
            params["groupId"] = group_id
        if asset_id:
            params["search"] = asset_id
        
        print(f" Searching for assets in Exchange...")
        print(f" GET {url}")
        print(f" Parameters: {params}")
            
        try:
            response = self.session.get(url, params=params)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            print(f" Response Body: {truncate_json_response(data)}")
            

            print(f" Found {len(data)} assets")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f" Failed to search assets: {e}")
            return []
    
    def get_asset_details(self, group_id: str, asset_id: str, version: str, org_id: str) -> Optional[Dict]:
        """Get detailed information about a specific asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}"
        
        params = {"organizationId": org_id}
        
        print(f" Fetching asset details for {group_id}/{asset_id}:{version}")
        print(f" GET {url}")
        print(f" Parameters: {params}")
        
        try:
            response = self.session.get(url, params=params)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()
            print(f" Response Body: {truncate_json_response(response.json())}")
            print(f" Successfully retrieved asset details")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f" Failed to get asset details for {asset_id}: {e}")
            return None
    
    def download_asset_files(self, group_id: str, asset_id: str, version: str, org_id: str) -> Dict[str, Any]:
        """Download files associated with an asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}/files"
        
        params = {"organizationId": org_id}
        
        print(f" Fetching file list for {group_id}/{asset_id}:{version}")
        print(f" GET {url}")
        print(f" Parameters: {params}")
        
        try:
            response = self.session.get(url, params=params)
            print(f" Response Status: {response.status_code}")
            response.raise_for_status()
            
            files_data = response.json()
            print(f" Response Body: {truncate_json_response(files_data)}")
            
            files = files_data.get('files', [])
            print(f" Found {len(files)} files for asset")
            return files_data
            
        except requests.exceptions.RequestException as e:
            print(f" Failed to get asset files for {asset_id}: {e}")
            return {}
    
    def download_file_content(self, download_url: str, file_name: str = "unknown") -> Optional[bytes]:
        """Download file content from a URL"""
        print(f" Downloading file: {file_name}")
        print(f" GET {download_url}")
        
        try:
            response = self.session.get(download_url)
            print(f" Response Status: {response.status_code}")
            print(f" Content Length: {len(response.content)} bytes")
            response.raise_for_status()
            
            # Log response body based on content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' in content_type:
                try:
                    json_data = response.json()
                    print(f" Response Body: {truncate_json_response(json_data)}")
                except:
                    print(f" Response Body: Failed to parse JSON")
            elif any(text_type in content_type for text_type in ['text/', 'application/yaml', 'application/xml']):
                # For text-based files, show first part of content
                text_content = response.text[:500]
                print(f" Response Body (first 500 chars): {text_content}")
                if len(response.text) > 500:
                    print(f"... (truncated, total length: {len(response.text)} chars)")
            else:
                print(f" Response Body: Binary data ({content_type})")
            
            print(f" Successfully downloaded {file_name}")
            return response.content
            
        except requests.exceptions.RequestException as e:
            print(f" Failed to download file {file_name}: {e}")
            return None
    
    def get_portal_info(self, group_id: str, asset_id: str, version: str) -> Optional[Dict]:
        """Get portal information for an asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}/portal"
        
        print(f" Fetching portal info for {group_id}/{asset_id}:{version}")
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
    
    def get_portal_pages(self, group_id: str, asset_id: str, version: str) -> Optional[List[Dict]]:
        """Get portal pages for an asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}/portal/pages"
        
        print(f" Fetching portal pages for {group_id}/{asset_id}:{version}")
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

    def get_portal_page_content(self, group_id: str, asset_id: str, version: str, page_path: str) -> Optional[Dict]:
        """Get content of a specific portal page using its path"""
        # URL encode the page path to handle spaces and special characters
        import urllib.parse
        encoded_path = urllib.parse.quote(page_path, safe='/')
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}/portal/pages/{encoded_path}"
        
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
                page_content = {
                    "path": page_path,
                    "content_type": content_type,
                    "content": text_content,
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


def is_zip_file(content: bytes) -> bool:
    """Check if content is a zip file by examining the magic bytes"""
    return content.startswith(b'PK\x03\x04') or content.startswith(b'PK\x05\x06') or content.startswith(b'PK\x07\x08')


def unzip_file(zip_path: Path, extract_to: Path) -> bool:
    """Unzip a file to the specified directory"""
    try:
        print(f" Unzipping: {zip_path.name}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List contents
            file_list = zip_ref.namelist()
            print(f"  Archive contains {len(file_list)} files:")
            for file_name in file_list[:5]:  # Show first 5 files
                print(f"    • {file_name}")
            if len(file_list) > 5:
                print(f"    ... and {len(file_list) - 5} more files")
            
            # Extract all files
            zip_ref.extractall(extract_to)
            print(f"  Extracted to: {extract_to}")
            
            # Remove the original zip file
            zip_path.unlink()
            print(f"  Removed original zip file: {zip_path.name}")
            
            return True
            
    except zipfile.BadZipFile:
        print(f"  Invalid zip file: {zip_path.name}")
        return False
    except Exception as e:
        print(f"  Failed to unzip {zip_path.name}: {e}")
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


def extract_categories_from_asset_details(asset_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract categories from asset details and convert to tagKey format"""
    categories = []
    
    # Get categories from asset details
    asset_categories = asset_details.get('categories', [])
    
    if asset_categories:
        print(f"  Found {len(asset_categories)} categories in asset")
        for category in asset_categories:
            if isinstance(category, dict) and 'key' in category and 'value' in category:
                categories.append({
                    "tagKey": category['key'],
                    "value": category['value']
                })
                print(f"    • {category['key']}: {category['value']}")
    
    return categories


def save_consolidated_categories(all_categories: List[Dict[str, Any]], output_dir: Path) -> bool:
    """Save consolidated categories to categories.json"""
    if not all_categories:
        return False
    
    # Remove duplicates based on tagKey
    unique_categories = {}
    for category in all_categories:
        tag_key = category['tagKey']
        if tag_key not in unique_categories:
            unique_categories[tag_key] = category
        else:
            # Merge values if they're different
            existing_values = set(unique_categories[tag_key]['value'])
            new_values = set(category['value'])
            merged_values = list(existing_values.union(new_values))
            unique_categories[tag_key]['value'] = merged_values
    
    categories_list = list(unique_categories.values())
    categories_file = output_dir / "categories.json"
    
    try:
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(categories_list, f, indent=2, ensure_ascii=False)
        
        print(f" Saved consolidated categories: {categories_file}")
        print(f" Total unique categories: {len(categories_list)}")
        for category in categories_list:
            print(f"  • {category['tagKey']}: {category['value']}")
        
        return True
    except Exception as e:
        print(f" Failed to save categories.json: {e}")
        return False


def main():
    """Main function to download API specs from Anypoint Exchange"""
    
    start_time = time.time()
    
    # Get environment variables
    # client_id = os.getenv('CLIENT_ID')
    # client_secret = os.getenv('CLIENT_SECRET')
    # exchange_url = os.getenv('EXCHANGE_URL', 'https://anypoint.mulesoft.com')
    # org_id = os.getenv('ORGANIZATION_ID')
    # asset_id = os.getenv('ASSET_ID')
    # group_id = os.getenv('GROUP_ID')
    # output_dir = os.getenv('OUTPUT_DIR', 'api-specs')
    # include_docs = os.getenv('INCLUDE_DOCS', 'true').lower() == 'true'
    # include_metadata = os.getenv('INCLUDE_METADATA', 'true').lower() == 'true'

    client_id = "9fb175fef85e4b7fbc028166a30d8448"
    client_secret = "909E56b28ff545169843C9cc3E40BfD2"
    exchange_url = 'https://anypoint.mulesoft.com'
    org_id = '1bb53e2e-0362-40c7-80cc-273290c8d74b'
    asset_id = 'openapi'
    group_id = org_id
    output_dir = os.getenv('OUTPUT_DIR', 'api-specs')
    include_docs = os.getenv('INCLUDE_DOCS', 'true').lower() == 'true'
    include_metadata = os.getenv('INCLUDE_METADATA', 'true').lower() == 'true'
    
    # Validate required environment variables
    if not client_id or not client_secret:
        print(" CLIENT_ID and CLIENT_SECRET environment variables are required")
        sys.exit(1)
    
    if not org_id:
        print(" ORGANIZATION_ID environment variable is required")
        sys.exit(1)
    
    print(f" Starting MuleSoft Anypoint Exchange API spec download...")
    print(f" Output directory: {output_dir}")
    print(f" Organization ID: {org_id}")
    print(f" Asset ID filter: {asset_id if asset_id else 'None (all assets)'}")
    print(f" Group ID filter: {group_id if group_id else 'None (all groups)'}")
    print(f" Include documentation: {include_docs}")
    print(f" Include metadata: {include_metadata}")
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
    
    # Search for assets
    print("=" * 60)
    print(f" Searching for assets...")
    assets = client.search_assets(org_id, group_id, asset_id)
    
    if not assets:
        print(" No assets found")
        sys.exit(0)
    
    print(f" Found {len(assets)} assets to process")
    print("=" * 60)
    
    # Filter to latest versions
    latest_assets = get_latest_assets(assets)
    
    downloaded_count = 0
    processed_count = 0
    docs_downloaded_count = 0
    all_categories = []
    
    for i, asset in enumerate(latest_assets, 1):
        asset_group_id = asset.get('groupId')
        asset_asset_id = asset.get('assetId')
        asset_version = asset.get('version')
        
        print(f"\n Processing asset {i}/{len(latest_assets)}: {asset_group_id}/{asset_asset_id}:{asset_version}")
        
        if not all([asset_group_id, asset_asset_id, asset_version]):
            print(f" Skipping asset with missing identifiers: {asset}")
            continue
        
        processed_count += 1
        
        print(f" Processing asset: {asset_group_id}/{asset_asset_id}:{asset_version}")
        
        # Create asset directory
        asset_dir = output_path / f"{asset_asset_id}_{asset_version}"
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        # Get asset details
        asset_details = client.get_asset_details(asset_group_id, asset_asset_id, asset_version, org_id)
        
        if asset_details and include_metadata:
            # Save asset metadata
            metadata_file = asset_dir / "metadata.json"
            save_json(asset_details, metadata_file)
            print(f" Saved metadata: {metadata_file}")
            
            # Extract categories from asset details
            categories = extract_categories_from_asset_details(asset_details)
            all_categories.extend(categories)
        
        if include_docs:
            print(f" Downloading documentation for {asset_asset_id}...")
            
            # Get portal information
            portal_info = client.get_portal_info(asset_group_id, asset_asset_id, asset_version)
            if portal_info:
                portal_file = asset_dir / "portal_info.json"
                save_json(portal_info, portal_file)
                print(f" Saved portal info: {portal_file}")
                docs_downloaded_count += 1
            
            # Get portal pages
            portal_pages = client.get_portal_pages(asset_group_id, asset_asset_id, asset_version)
            if portal_pages:
                pages_file = asset_dir / "portal_pages.json"
                save_json(portal_pages, pages_file)
                print(f" Saved portal pages: {pages_file}")
                
                # Save individual pages as separate files for easier access
                pages_dir = asset_dir / "pages"
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
                    page_content = client.get_portal_page_content(asset_group_id, asset_asset_id, asset_version, page_path)
                    if page_content:
                        content_file = pages_dir / f"{safe_filename}_content.json"
                        save_json(page_content, content_file)
                        print(f" Saved page content: {content_file}")
                        docs_downloaded_count += 1
                        
                        if MARKDOWNIFY_AVAILABLE and 'content' in page_content and page_content['content_type'].startswith('text/html'):
                            markdown_file = pages_dir / f"{markdown_name}.md"
                            markdown_content = md(page_content['content'])
                            save_markdown(markdown_content, markdown_file)
                            print(f" Saved page content as Markdown: {markdown_file}")
                            docs_downloaded_count += 1
                    
                    # Add small delay to avoid rate limiting
                    time.sleep(0.1)
        
        # Use files from asset details instead of separate API call
        files = asset_details.get('files', []) if asset_details else []
        
        if not files:
            print(f" No files found for asset {asset_asset_id}")
            continue
        
        print(f" Found {len(files)} files to process")
        
        for j, file_info in enumerate(files, 1):
            # Generate filename from classifier and packaging if fileName not present
            classifier = file_info.get('classifier', 'unknown')
            packaging = file_info.get('packaging', '')
            file_name = file_info.get('fileName')

            if classifier != 'oas':
                print(f" Skip downloading non-OAS file: {file_name}")
                continue

            if not file_name:
                file_name = f"{asset_asset_id}-{asset_version}-{classifier}"
                if packaging:
                    file_name += f".{packaging}"
            
            download_url = file_info.get('downloadURL')
            
            print(f"  Processing file {j}/{len(files)}: {file_name}")
            print(f"  Classifier: {classifier}, Packaging: {packaging}")
            
            if not download_url:
                print(f"  No download URL for file: {file_name}")
                continue
            
            # Check if it's an OpenAPI spec file based on classifier or filename
            is_openapi = (classifier and 'oas' in classifier.lower()) or \
                        any(keyword in file_name.lower() for keyword in 
                           ['openapi', 'swagger', 'api-spec', '.yaml', '.yml', '.json'])
            
            # Check if it's documentation
            is_doc = any(keyword in file_name.lower() for keyword in 
                        ['doc', 'readme', 'guide', '.md', '.html', '.pdf'])
            
            # Identify file type for logging
            file_type = " OpenAPI Spec" if is_openapi else " Documentation" if is_doc else " Other"
            print(f"  File type: {file_type}")
            
            # Skip non-relevant files if not including docs
            if not include_docs and is_doc and not is_openapi:
                print(f"  Skipping documentation file (include_docs=False)")
                continue
            
            # Download file content
            content = client.download_file_content(download_url, file_name)
            
            if content:
                file_path = asset_dir / file_name
                
                # First save the file
                if save_file(content, file_path):
                    print(f"  Saved: {file_path.relative_to(output_path)}")
                    
                    # Check if it's a zip file and unzip it
                    if is_zip_file(content):
                        print(f"  Zip file detected: {file_name}")
                        zip_dir = asset_dir / f"{file_name.rsplit('.', 1)[0]}_extracted"
                        if unzip_file(file_path, zip_dir):
                            print(f"  Successfully unzipped {file_name} to {zip_dir.name}")
                        else:
                            print(f"  Failed to unzip {file_name}")
                    
                    if is_openapi:
                        downloaded_count += 1
                        print(f"  OpenAPI spec count: {downloaded_count}")
                else:
                    print(f"  Failed to save: {file_name}")
            else:
                print(f"  Failed to download: {file_name}")
            
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
        
        print(f" Completed processing asset {i}/{len(latest_assets)}")
        print("-" * 40)
    
    # Save consolidated categories
    if all_categories:
        save_consolidated_categories(all_categories, output_path)
    
    # Create summary file
    summary = {
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "total_assets_found": len(assets),
        "latest_assets_processed": len(latest_assets),
        "specs_downloaded": downloaded_count,
        "docs_downloaded": docs_downloaded_count,
        "categories_extracted": len(all_categories),
        "unique_categories": len(set(cat['tagKey'] for cat in all_categories)) if all_categories else 0,
        "output_directory": str(output_path),
        "duration_seconds": round(time.time() - start_time, 2)
    }
    
    summary_file = output_path / "download_summary.json"
    save_json(summary, summary_file)
    
    print("\n" + "=" * 60)
    print(" DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f" Duration: {summary['duration_seconds']} seconds")
    print(f" Assets found: {summary['total_assets_found']}")
    print(f" Latest versions processed: {summary['latest_assets_processed']}")
    print(f" API specs downloaded: {summary['specs_downloaded']}")
    print(f" Documentation downloaded: {summary['docs_downloaded']}")
    print(f" Categories extracted: {summary['categories_extracted']}")
    print(f" Unique categories: {summary['unique_categories']}")
    print(f" Output directory: {summary['output_directory']}")
    print(f" Summary saved: {summary_file}")
    
    # Set GitHub Actions outputs
    if os.getenv('GITHUB_ACTIONS'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"specs-count={downloaded_count}\n")
            f.write(f"docs-count={docs_downloaded_count}\n")
            f.write(f"categories-count={len(set(cat['tagKey'] for cat in all_categories)) if all_categories else 0}\n")
            f.write(f"output-path={output_path}\n")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\n Download completed in {elapsed_time:.2f} seconds!")
    print(f" Total assets processed: {len(latest_assets)}")
    print(f" OpenAPI specs downloaded: {downloaded_count}")
    print(f" Documentation items downloaded: {docs_downloaded_count}")
    print(f" Files saved to: {output_path.absolute()}")


if __name__ == "__main__":
    main()
