#!/bin/bash

# MuleSoft Anypoint CLI API Spec Downloader
# This script downloads OpenAPI specifications from MuleSoft Anypoint Exchange using the Anypoint CLI
# It uses the same .env file approach as the Python download_specs.py script

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

CLIENT_ID="9fb175fef85e4b7fbc028166a30d8448"
CLIENT_SECRET="909E56b28ff545169843C9cc3E40BfD2"
ORG_ID="1bb53e2e-0362-40c7-80cc-273290c8d74b"

ASSET_ID="openapi"
ASSET_VERSION="1.0.0"

# Configure Credentials
configure_credentials() {
  anypoint-cli-v4 conf client_id "$CLIENT_ID"
  anypoint-cli-v4 conf client_secret "$CLIENT_SECRET"
  anypoint-cli-v4 conf organization "$ORG_ID"

  anypoint-cli-v4 account:environment:list
}

export_api_specs() {
  anypoint-cli-v4 exchange:asset:download "$ASSET_ID/${ASSET_VERSION}" ./api-spec
  cd api-spec && ls -t *.zip 2>/dev/null | head -1 | xargs -I {} unzip "{}" && mv *.yaml ../


}

configure_credentials
export_api_specs