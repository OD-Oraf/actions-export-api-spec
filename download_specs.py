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
from pathlib import Path
from typing import Dict, List, Optional, Any
import time


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
    
    print(f"🔍 Processing {len(assets)} assets to find latest versions...")
    
    for asset in assets:
        asset_id = asset.get('assetId')
        group_id = asset.get('groupId')
        version = asset.get('version')
        
        if not all([asset_id, group_id, version]):
            print(f"⚠️ Skipping asset with missing identifiers: {asset}")
            continue
            
        # Create a unique key for each asset (groupId + assetId)
        key = f"{group_id}/{asset_id}"
        
        if key not in asset_groups:
            asset_groups[key] = asset
            print(f"📝 New asset: {key} v{version}")
        else:
            # Compare versions and keep the latest
            current_version = parse_version(asset_groups[key].get('version', '0'))
            new_version = parse_version(version)
            
            if new_version > current_version:
                old_version = asset_groups[key].get('version')
                asset_groups[key] = asset
                print(f"🔄 Updated {key}: v{old_version} → v{version}")
            else:
                print(f"⏭️ Keeping {key}: v{asset_groups[key].get('version')} (skipping v{version})")
    
    latest_assets = list(asset_groups.values())
    print(f"✅ Filtered to {len(latest_assets)} latest versions from {len(assets)} total assets")
    
    # Show final selection
    print("\n📋 Final asset selection (latest versions only):")
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
        
        print(f"🔐 Getting access token...")
        print(f"📡 POST {auth_url}")
        
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
            print(f"📊 Response Status: {response.status_code}")
            response.raise_for_status()
            
            auth_data = response.json()
            self.access_token = auth_data.get("access_token")
            
            if self.access_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                })
                print("✅ Successfully generated Anypoint Platform access token")
                print(f"📝 Response Body: {truncate_json_response(auth_data)}")
                return True
            else:
                print("❌ Failed to get access token from response")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def get_organizations(self) -> List[Dict]:
        """Get list of organizations the user has access to"""
        # MuleSoft Anypoint Platform API endpoint for user profile
        url = f"{self.base_url}/accounts/api/profile"
        
        print(f"🏢 Fetching user organizations...")
        print(f"📡 GET {url}")
        
        try:
            response = self.session.get(url)
            print(f"📊 Response Status: {response.status_code}")
            response.raise_for_status()
            user_data = response.json()
            print(f"📝 Response Body: {truncate_json_response(user_data)}")
            
            orgs = user_data.get("memberOfOrganizations", [])
            print(f"✅ Found {len(orgs)} organizations")
            return orgs
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get organizations: {e}")
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
        
        print(f"🔍 Searching for assets in Exchange...")
        print(f"📡 GET {url}")
        print(f"📋 Parameters: {params}")
            
        try:
            response = self.session.get(url, params=params)
            print(f"📊 Response Status: {response.status_code}")
            response.raise_for_status()
            
            data = response.json()
            print(f"📝 Response Body: {truncate_json_response(data)}")
            

            print(f"✅ Found {len(data)} assets")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to search assets: {e}")
            return []
    
    def get_asset_details(self, group_id: str, asset_id: str, version: str, org_id: str) -> Optional[Dict]:
        """Get detailed information about a specific asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}"
        
        params = {"organizationId": org_id}
        
        print(f"📋 Fetching asset details for {group_id}/{asset_id}:{version}")
        print(f"📡 GET {url}")
        print(f"📋 Parameters: {params}")
        
        try:
            response = self.session.get(url, params=params)
            print(f"📊 Response Status: {response.status_code}")
            response.raise_for_status()
            print(f"📝 Response Body: {truncate_json_response(response.json())}")
            print(f"✅ Successfully retrieved asset details")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get asset details for {asset_id}: {e}")
            return None
    
    def download_asset_files(self, group_id: str, asset_id: str, version: str, org_id: str) -> Dict[str, Any]:
        """Download files associated with an asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}/files"
        
        params = {"organizationId": org_id}
        
        print(f"📁 Fetching file list for {group_id}/{asset_id}:{version}")
        print(f"📡 GET {url}")
        print(f"📋 Parameters: {params}")
        
        try:
            response = self.session.get(url, params=params)
            print(f"📊 Response Status: {response.status_code}")
            response.raise_for_status()
            
            files_data = response.json()
            print(f"📝 Response Body: {truncate_json_response(files_data)}")
            
            files = files_data.get('files', [])
            print(f"✅ Found {len(files)} files for asset")
            return files_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get asset files for {asset_id}: {e}")
            return {}
    
    def download_file_content(self, download_url: str, file_name: str = "unknown") -> Optional[bytes]:
        """Download file content from a URL"""
        print(f"⬇️ Downloading file: {file_name}")
        print(f"📡 GET {download_url}")
        
        try:
            response = self.session.get(download_url)
            print(f"📊 Response Status: {response.status_code}")
            print(f"📏 Content Length: {len(response.content)} bytes")
            response.raise_for_status()
            
            # Log response body based on content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' in content_type:
                try:
                    json_data = response.json()
                    print(f"📝 Response Body: {truncate_json_response(json_data)}")
                except:
                    print(f"📝 Response Body: Failed to parse JSON")
            elif any(text_type in content_type for text_type in ['text/', 'application/yaml', 'application/xml']):
                # For text-based files, show first part of content
                text_content = response.text[:500]
                print(f"📝 Response Body (first 500 chars): {text_content}")
                if len(response.text) > 500:
                    print(f"... (truncated, total length: {len(response.text)} chars)")
            else:
                print(f"📝 Response Body: Binary data ({content_type})")
            
            print(f"✅ Successfully downloaded {file_name}")
            return response.content
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to download file {file_name}: {e}")
            return None


def save_file(content: bytes, file_path: Path) -> bool:
    """Save content to a file"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"❌ Failed to save file {file_path}: {e}")
        return False


def save_json(data: Dict, file_path: Path) -> bool:
    """Save JSON data to a file"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Failed to save JSON file {file_path}: {e}")
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
        print("❌ CLIENT_ID and CLIENT_SECRET environment variables are required")
        sys.exit(1)
    
    if not org_id:
        print("❌ ORGANIZATION_ID environment variable is required")
        sys.exit(1)
    
    print(f"🚀 Starting MuleSoft Anypoint Exchange API spec download...")
    print(f"📁 Output directory: {output_dir}")
    print(f"🏢 Organization ID: {org_id}")
    print(f"🔍 Asset ID filter: {asset_id if asset_id else 'None (all assets)'}")
    print(f"👥 Group ID filter: {group_id if group_id else 'None (all groups)'}")
    print(f"📚 Include documentation: {include_docs}")
    print(f"🏷️ Include metadata: {include_metadata}")
    print(f"🌐 Exchange URL: {exchange_url}")
    print("=" * 60)
    
    # Initialize client and authenticate
    client = AnypointExchangeClient(exchange_url, client_id, client_secret)
    
    if not client.authenticate():
        print("❌ Failed to authenticate with Anypoint Platform")
        sys.exit(1)
    
    print("=" * 60)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"📂 Created output directory: {output_path.absolute()}")
    
    # Search for assets
    print("=" * 60)
    print(f"🔍 Searching for assets...")
    assets = client.search_assets(org_id, group_id, asset_id)
    
    if not assets:
        print("⚠️ No assets found")
        sys.exit(0)
    
    print(f"📦 Found {len(assets)} assets to process")
    print("=" * 60)
    
    # Filter to latest versions
    latest_assets = get_latest_assets(assets)
    
    downloaded_count = 0
    processed_count = 0
    
    for i, asset in enumerate(latest_assets, 1):
        asset_group_id = asset.get('groupId')
        asset_asset_id = asset.get('assetId')
        asset_version = asset.get('version')
        
        print(f"\n🔄 Processing asset {i}/{len(latest_assets)}: {asset_group_id}/{asset_asset_id}:{asset_version}")
        
        if not all([asset_group_id, asset_asset_id, asset_version]):
            print(f"⚠️ Skipping asset with missing identifiers: {asset}")
            continue
        
        processed_count += 1
        
        print(f"📋 Processing asset: {asset_group_id}/{asset_asset_id}:{asset_version}")
        
        # Create asset directory
        asset_dir = output_path / f"{asset_asset_id}_{asset_version}"
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        # Get asset details
        asset_details = client.get_asset_details(asset_group_id, asset_asset_id, asset_version, org_id)
        
        if asset_details and include_metadata:
            # Save asset metadata
            metadata_file = asset_dir / "metadata.json"
            save_json(asset_details, metadata_file)
            print(f"💾 Saved metadata: {metadata_file}")
        
        # Use files from asset details instead of separate API call
        files = asset_details.get('files', []) if asset_details else []
        
        if not files:
            print(f"⚠️ No files found for asset {asset_asset_id}")
            continue
        
        print(f"📁 Found {len(files)} files to process")
        
        for j, file_info in enumerate(files, 1):
            # Generate filename from classifier and packaging if fileName not present
            classifier = file_info.get('classifier', 'unknown')
            packaging = file_info.get('packaging', '')
            file_name = file_info.get('fileName')

            if classifier != 'oas':
                print(f"⚠️ Skip downloading non-OAS file: {file_name}")
                continue

            if not file_name:
                file_name = f"{asset_asset_id}-{asset_version}-{classifier}"
                if packaging:
                    file_name += f".{packaging}"
            
            download_url = file_info.get('downloadURL')
            
            print(f"  📄 Processing file {j}/{len(files)}: {file_name}")
            print(f"  🏷️ Classifier: {classifier}, Packaging: {packaging}")
            
            if not download_url:
                print(f"  ⚠️ No download URL for file: {file_name}")
                continue
            
            # Check if it's an OpenAPI spec file based on classifier or filename
            is_openapi = (classifier and 'oas' in classifier.lower()) or \
                        any(keyword in file_name.lower() for keyword in 
                           ['openapi', 'swagger', 'api-spec', '.yaml', '.yml', '.json'])
            
            # Check if it's documentation
            is_doc = any(keyword in file_name.lower() for keyword in 
                        ['doc', 'readme', 'guide', '.md', '.html', '.pdf'])
            
            # Identify file type for logging
            file_type = "📄 OpenAPI Spec" if is_openapi else "📚 Documentation" if is_doc else "📎 Other"
            print(f"  🏷️ File type: {file_type}")
            
            # Skip non-relevant files if not including docs
            if not include_docs and is_doc and not is_openapi:
                print(f"  ⏭️ Skipping documentation file (include_docs=False)")
                continue
            
            # Download file content
            content = client.download_file_content(download_url, file_name)
            
            if content:
                file_path = asset_dir / file_name
                if save_file(content, file_path):
                    print(f"  ✅ Saved: {file_path.relative_to(output_path)}")
                    if is_openapi:
                        downloaded_count += 1
                        print(f"  🎯 OpenAPI spec count: {downloaded_count}")
                else:
                    print(f"  ❌ Failed to save: {file_name}")
            else:
                print(f"  ❌ Failed to download: {file_name}")
            
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
        
        print(f"✅ Completed processing asset {i}/{len(latest_assets)}")
        print("-" * 40)
    
    # Create summary file
    summary = {
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "organization_id": org_id,
        "total_assets": len(latest_assets),
        "openapi_specs_downloaded": downloaded_count,
        "output_directory": str(output_path.absolute()),
        "settings": {
            "include_documentation": include_docs,
            "include_metadata": include_metadata,
            "group_id_filter": group_id,
            "asset_id_filter": asset_id
        }
    }
    
    summary_file = output_path / "download_summary.json"
    save_json(summary, summary_file)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\n✅ Download completed in {elapsed_time:.2f} seconds!")
    print(f"📊 Total assets processed: {len(latest_assets)}")
    print(f"📄 OpenAPI specs downloaded: {downloaded_count}")
    print(f"📁 Files saved to: {output_path.absolute()}")
    
    # Set GitHub Actions outputs
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
            f.write(f"specs-count={downloaded_count}\n")
            f.write(f"output-path={output_path.absolute()}\n")


if __name__ == "__main__":
    main()
