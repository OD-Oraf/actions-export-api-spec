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
  anypoint-cli-v4 exchange:asset:download "${ASSET_ID}/${ASSET_VERSION}" ./"${EXPORT_DIR}"
  cd "${EXPORT_DIR}" && ls -t *.zip 2>/dev/null | head -1 | xargs -I {} unzip "{}"


}

configure_credentials
export_api_specs