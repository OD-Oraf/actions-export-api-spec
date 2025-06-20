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


class AnypointExchangeClient:
    """Client for interacting with MuleSoft Anypoint Exchange API"""
    
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.session = requests.Session()
        
    def authenticate(self) -> bool:
        """Authenticate with Anypoint Platform and get access token"""
        auth_url = f"{self.base_url}/accounts/login"
        
        payload = {
            "username": self.client_id,
            "password": self.client_secret
        }
        
        try:
            response = self.session.post(auth_url, json=payload)
            response.raise_for_status()
            
            auth_data = response.json()
            self.access_token = auth_data.get("access_token")
            
            if self.access_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                })
                print("✅ Successfully authenticated with Anypoint Platform")
                return True
            else:
                print("❌ Failed to get access token from response")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def get_organizations(self) -> List[Dict]:
        """Get list of organizations the user has access to"""
        url = f"{self.base_url}/accounts/api/me"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            user_data = response.json()
            
            return user_data.get("user", {}).get("memberOfOrganizations", [])
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
            
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("assets", [])
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to search assets: {e}")
            return []
    
    def get_asset_details(self, group_id: str, asset_id: str, version: str, org_id: str) -> Optional[Dict]:
        """Get detailed information about a specific asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}"
        
        params = {"organizationId": org_id}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get asset details for {asset_id}: {e}")
            return None
    
    def download_asset_files(self, group_id: str, asset_id: str, version: str, org_id: str) -> Dict[str, Any]:
        """Download files associated with an asset"""
        url = f"{self.base_url}/exchange/api/v2/assets/{group_id}/{asset_id}/{version}/files"
        
        params = {"organizationId": org_id}
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get asset files for {asset_id}: {e}")
            return {}
    
    def download_file_content(self, download_url: str) -> Optional[bytes]:
        """Download file content from a URL"""
        try:
            response = self.session.get(download_url)
            response.raise_for_status()
            return response.content
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to download file: {e}")
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
    
    # Get environment variables
    client_id = os.getenv('CLIENT_ID')
    client_secret = os.getenv('CLIENT_SECRET')
    exchange_url = os.getenv('EXCHANGE_URL', 'https://anypoint.mulesoft.com')
    org_id = os.getenv('ORGANIZATION_ID')
    asset_id = os.getenv('ASSET_ID')
    group_id = os.getenv('GROUP_ID')
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
    
    # Initialize client and authenticate
    client = AnypointExchangeClient(exchange_url, client_id, client_secret)
    
    if not client.authenticate():
        print("❌ Failed to authenticate with Anypoint Platform")
        sys.exit(1)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Search for assets
    print(f"🔍 Searching for assets...")
    assets = client.search_assets(org_id, group_id, asset_id)
    
    if not assets:
        print("⚠️ No assets found")
        sys.exit(0)
    
    print(f"📦 Found {len(assets)} assets")
    
    downloaded_count = 0
    
    for asset in assets:
        asset_group_id = asset.get('groupId')
        asset_asset_id = asset.get('assetId')
        asset_version = asset.get('version')
        
        if not all([asset_group_id, asset_asset_id, asset_version]):
            print(f"⚠️ Skipping asset with missing identifiers: {asset}")
            continue
        
        print(f"\n📋 Processing asset: {asset_group_id}/{asset_asset_id}:{asset_version}")
        
        # Create asset directory
        asset_dir = output_path / f"{asset_group_id}_{asset_asset_id}_{asset_version}"
        asset_dir.mkdir(parents=True, exist_ok=True)
        
        # Get asset details
        asset_details = client.get_asset_details(asset_group_id, asset_asset_id, asset_version, org_id)
        
        if asset_details and include_metadata:
            # Save asset metadata
            metadata_file = asset_dir / "metadata.json"
            save_json(asset_details, metadata_file)
            print(f"💾 Saved metadata: {metadata_file}")
        
        # Download asset files
        files_info = client.download_asset_files(asset_group_id, asset_asset_id, asset_version, org_id)
        
        if not files_info:
            print(f"⚠️ No files found for asset {asset_asset_id}")
            continue
        
        files = files_info.get('files', [])
        
        for file_info in files:
            file_name = file_info.get('fileName', 'unknown')
            download_url = file_info.get('downloadURL')
            
            if not download_url:
                print(f"⚠️ No download URL for file: {file_name}")
                continue
            
            # Check if it's an OpenAPI spec file
            is_openapi = any(keyword in file_name.lower() for keyword in 
                           ['openapi', 'swagger', 'api-spec', '.yaml', '.yml', '.json'])
            
            # Check if it's documentation
            is_doc = any(keyword in file_name.lower() for keyword in 
                        ['doc', 'readme', 'guide', '.md', '.html', '.pdf'])
            
            # Skip non-relevant files if not including docs
            if not include_docs and is_doc and not is_openapi:
                continue
            
            print(f"⬇️ Downloading: {file_name}")
            
            # Download file content
            content = client.download_file_content(download_url)
            
            if content:
                file_path = asset_dir / file_name
                if save_file(content, file_path):
                    print(f"💾 Saved: {file_path}")
                    if is_openapi:
                        downloaded_count += 1
            
            # Add small delay to avoid rate limiting
            time.sleep(0.1)
    
    # Create summary file
    summary = {
        "download_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "organization_id": org_id,
        "total_assets": len(assets),
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
    
    print(f"\n✅ Download completed!")
    print(f"📊 Total assets processed: {len(assets)}")
    print(f"📄 OpenAPI specs downloaded: {downloaded_count}")
    print(f"📁 Files saved to: {output_path.absolute()}")
    
    # Set GitHub Actions outputs
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
            f.write(f"specs-count={downloaded_count}\n")
            f.write(f"output-path={output_path.absolute()}\n")


if __name__ == "__main__":
    main()
