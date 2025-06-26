#!/bin/bash

# MuleSoft Anypoint CLI API Spec Downloader
# This script downloads OpenAPI specifications from MuleSoft Anypoint Exchange using the Anypoint CLI
# It uses the same .env file approach as the Python download_specs.py script

set -ex    # Exit on error, undefined variables, and pipe failures



# Configure Credentials
configure_credentials() {
  anypoint-cli-v4 conf client_id "$CLIENT_ID"
  anypoint-cli-v4 conf client_secret "$CLIENT_SECRET"
  anypoint-cli-v4 conf organization "$ORGANIZATION_ID"

  anypoint-cli-v4 account:environment:list
}

export_api_specs() {
  echo "📥 Downloading asset ${ASSET_ID}/${ASSET_VERSION} to ${EXPORT_DIR}..."
  anypoint-cli-v4 exchange:asset:download "${ASSET_ID}/${ASSET_VERSION}" ./"${EXPORT_DIR}"
#  cd "${EXPORT_DIR}" && ls -t *.zip 2>/dev/null | head -1 | xargs -I {} unzip "{}"

  echo "📦 Processing downloaded files..."
  cd "${EXPORT_DIR}"

  # Check if zip files exist and extract them
  if ls *.zip 1> /dev/null 2>&1; then
    echo "🔓 Found zip files, extracting..."
    for zipfile in *.zip; do
      echo "  Extracting: $zipfile"
      unzip -o "$zipfile"
      rm "$zipfile"  # Clean up zip file after extraction
    done
  else
    echo "ℹ️  No zip files found to extract"
  fi

  # List extracted files
  echo "📄 Files in ${EXPORT_DIR}:"
  ls -la



}

configure_credentials
export_api_specs