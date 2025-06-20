# MuleSoft Anypoint Exchange API Spec Exporter

A GitHub Action that downloads OpenAPI specifications, documentation, and metadata from MuleSoft Anypoint Exchange using the Platform API.

## Features

- 🔐 Secure authentication using CLIENT_ID and CLIENT_SECRET
- 📄 Downloads OpenAPI/Swagger specifications
- 📚 Downloads documentation and related files
- 🏷️ Exports categories, tags, and metadata
- 📦 Stores all files as GitHub Actions artifacts
- 🔍 Supports filtering by organization, group, and asset ID

## MuleSoft API Endpoints Used

This action uses the following MuleSoft Anypoint Platform API endpoints:

- **Authentication**: `POST /accounts/api/v2/oauth2/token` - OAuth2 client credentials flow
- **User Profile**: `GET /accounts/api/profile` - Get user organizations
- **Asset Search**: `GET /exchange/api/v2/assets` - Search for assets in Exchange
- **Asset Details**: `GET /exchange/api/v2/assets/{groupId}/{assetId}/{version}` - Get asset metadata
- **Asset Files**: `GET /exchange/api/v2/assets/{groupId}/{assetId}/{version}/files` - Get downloadable files

## Prerequisites

Before using this action, you need to:

1. **Set up MuleSoft Anypoint Platform credentials**:
   - Obtain a CLIENT_ID and CLIENT_SECRET from your Anypoint Platform
   - Add these as repository secrets in GitHub

2. **Get your Organization ID**:
   - Log into Anypoint Platform
   - Navigate to Access Management
   - Note your Organization ID

## Usage

### Basic Usage

```yaml
name: Export API Specs
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * 1' # Weekly on Monday at 2 AM

jobs:
  export-specs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Export API Specs from Anypoint Exchange
        uses: ./
        env:
          CLIENT_ID: ${{ secrets.MULESOFT_CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.MULESOFT_CLIENT_SECRET }}
        with:
          organization-id: 'your-org-id-here'
          output-directory: 'downloaded-specs'
```

### Advanced Usage

```yaml
name: Export Specific API Specs
on:
  workflow_dispatch:
    inputs:
      asset_id:
        description: 'Specific Asset ID to download'
        required: false
        type: string

jobs:
  export-specs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      
      - name: Export API Specs from Anypoint Exchange
        uses: ./
        env:
          CLIENT_ID: ${{ secrets.MULESOFT_CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.MULESOFT_CLIENT_SECRET }}
        with:
          exchange-url: 'https://anypoint.mulesoft.com'
          organization-id: 'your-org-id-here'
          asset-id: ${{ github.event.inputs.asset_id }}
          group-id: 'your-group-id'
          output-directory: 'api-specs'
          include-documentation: 'true'
          include-metadata: 'true'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `exchange-url` | MuleSoft Anypoint Exchange URL | No | `https://anypoint.mulesoft.com` |
| `organization-id` | MuleSoft Organization ID | Yes | - |
| `asset-id` | Specific Asset ID to download (optional) | No | - |
| `group-id` | Group ID to filter assets | No | - |
| `output-directory` | Directory to store downloaded files | No | `api-specs` |
| `include-documentation` | Whether to download documentation | No | `true` |
| `include-metadata` | Whether to download categories and tags | No | `true` |

## Outputs

| Output | Description |
|--------|-------------|
| `specs-count` | Number of OpenAPI specifications downloaded |
| `output-path` | Path where files were downloaded |

## Environment Variables

The following environment variables must be set (typically as repository secrets):

- `CLIENT_ID`: Your MuleSoft Anypoint Platform Client ID
- `CLIENT_SECRET`: Your MuleSoft Anypoint Platform Client Secret

## File Structure

The action creates the following directory structure:

```
api-specs/
├── download_summary.json                 # Summary of the download process
├── groupId_assetId_version/              # Directory per asset
│   ├── metadata.json                     # Asset metadata (categories, tags, etc.)
│   ├── api-spec.yaml                     # OpenAPI specification
│   ├── documentation.md                  # Documentation files
│   └── ...                               # Other related files
└── ...
```

## Setting up Repository Secrets

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add the following secrets:
   - Name: `MULESOFT_CLIENT_ID`, Value: Your MuleSoft Client ID
   - Name: `MULESOFT_CLIENT_SECRET`, Value: Your MuleSoft Client Secret

## Getting MuleSoft Credentials

1. Log into [Anypoint Platform](https://anypoint.mulesoft.com)
2. Go to Access Management
3. Navigate to Connected Apps
4. Create a new Connected App or use an existing one
5. Note the Client ID and Client Secret
6. Ensure the app has the necessary scopes for Exchange access

## Troubleshooting

### Authentication Issues
- Verify your CLIENT_ID and CLIENT_SECRET are correct
- Ensure your Connected App has the right permissions
- Check that your organization ID is correct

### No Assets Found
- Verify the organization ID is correct
- Check if you have access to the specified assets
- Try removing group-id or asset-id filters

### Download Failures
- Check network connectivity
- Verify the Exchange URL is accessible
- Look for rate limiting issues in the logs

## Example Workflow

Here's a complete example workflow that runs weekly and uploads the results:

```yaml
name: Weekly API Spec Export

on:
  schedule:
    - cron: '0 2 * * 1' # Every Monday at 2 AM
  workflow_dispatch: # Allow manual triggering

jobs:
  export-api-specs:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      
      - name: Export API Specs from MuleSoft Exchange
        uses: ./
        id: export
        env:
          CLIENT_ID: ${{ secrets.MULESOFT_CLIENT_ID }}
          CLIENT_SECRET: ${{ secrets.MULESOFT_CLIENT_SECRET }}
        with:
          organization-id: ${{ vars.MULESOFT_ORG_ID }}
          output-directory: 'exported-specs'
          include-documentation: 'true'
          include-metadata: 'true'
      
      - name: Display results
        run: |
          echo "Downloaded ${{ steps.export.outputs.specs-count }} API specifications"
          echo "Files saved to: ${{ steps.export.outputs.output-path }}"
          ls -la exported-specs/
      
      # The artifacts are automatically uploaded by the action
      # You can access them in the Actions tab of your repository
```

## License

This action is available under the MIT License. See LICENSE file for details.
